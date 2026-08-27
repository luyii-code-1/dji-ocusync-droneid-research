# DJI OcuSync DroneID Research

[English](README.md) | [简体中文](README.zh-CN.md)

基于 HackRF 原始 IQ 的 DJI OcuSync O2/O4 DroneID 可复现实验记录与工具。

本仓库整理了截至 **2026-08-27** 已由原始采样、CRC 和连续遥测共同验证的结论。研究重点是接收链、物理层、包结构与密码学封装，并清晰标注已验证范围与待研究步骤。

## 目录

- [当前状态](#当前状态)
- [实测机型与发包触发条件](#实测机型与发包触发条件)
- [快速使用](#快速使用检查-aa-或解密-87)
- [完整研究记录](#完整研究记录)
- [O4 密码学链路](#o4-密码学链路)
- [可复现测量值](#可复现测量值与计算过程)
- [License](#license)

## 当前状态

| 环节 | 状态 | 验证方式 |
|---|---|---|
| HackRF int8 IQ 输入 | 已验证 | 实际录制与回放 |
| O2 9-symbol OFDM / ZC600+147 | 已验证 | 相关峰与帧结构 |
| O2 LTE Turbo transport | 已验证 | CRC24A 余数为 0 |
| O2 内层载荷 | 已验证 | DJI CRC16 余数为 0 |
| O4 AA/87 空口逻辑包 | 已验证 | 双 CRC 有效样本 |
| AA 的 C1 曲线点与 `C1‖C3‖C2` 布局 | 强证据 | 多会话曲线方程检查 |
| `note → 87` | 已验证 | AES-128-CTR 解出连续、合理遥测 |
| `AA → note` | 研究中 | 需要 SM2 私钥或等价解密模块 |

## 实测机型与发包触发条件

本仓库的 O4 测量与密码链样本来自 **DJI Mini 5 Pro**。实测触发条件如下：

- **GPS/GNSS 定位有效后开始发送 AA 关键材料包。**
- **操作者点击启动/起飞后开始发送 87 动态遥测包。**
- 仅飞行器开机尚未形成本文验证的 Mini 5 Pro AA/87 连续报文。
- 实测 O2/O3 行为不同：飞行器开机后即主动广播明文 DroneID 载荷，包括未连接遥控器的状态。

以上是对应实测机型与固件的协议行为，其他机型和版本需要分别复核。

目前确认的混合加密链：

```text
HackRF IQ
  → ZC / OFDM / Turbo
  → CRC24A + DJI CRC16
  → AA + 87

AA:
  SM2-compatible C1‖C3‖C2
  → 16-byte note                  （private-key step）

87:
  AES-128-CTR(key=note, IV=nonce8 || 0x00×8)
  → SN / UUID / drone / pilot / home telemetry
```

## 仓库内容

```text
src/o4_packet_tool.py       AA 结构检查与已知 note 的 87 本地解密
src/o2_droneid_decode.py    经典 O2 单帧 PHY/FEC 解码实验程序
src/droneid_hackrf_scanner.py
                            HackRF 实时/回放扫描器
tools/remove_turbo_soft.c   TurboFEC 适配器
```

## 快速使用：检查 AA 或解密 87

环境要求：Python 3.10+、OpenSSL 命令行。

```bash
python3 src/o4_packet_tool.py '<AA完整Hex>'
python3 src/o4_packet_tool.py --note '<16-byte-note-hex>' '<87完整Hex>'
```

`note` 是同一加密会话的 16 字节 AES 密钥。同一 `hashcode` 下的多个 87 使用同一 note、各自携带 nonce。会话刷新或飞行器重启导致 hashcode 改变后，必须获得新的 AA 对应 note。

当前工具覆盖 AA 结构验证，以及使用已知 note 解密同会话 87；AA 恢复 note 需要另行提供 SM2 私钥或等价解密模块。

## 采样率陷阱

HackRF 文件是交错的 signed int8 I/Q，每个 complex sample 为 2 字节。若使用：

```bash
hackrf_transfer -r capture.iq -f 2429500000 -s 20000000 -l 16 -g 20 -a 0
```

文件实际采样率就是 20 MS/s。经典检测器在 15.36 MS/s 工作时，必须先重采样：

```text
20.00 MS/s × 96 / 125 = 15.36 MS/s
```

分析器输入采样率必须与文件实际采样率一致；经典 15.36 MS/s 检测器处理 20 MS/s 采样时应先完成上述重采样，以保持 ZC 时间尺度、CP、FFT 窗口、CFO 和 CRC 链路一致。

## O2 解码器说明

`src/o2_droneid_decode.py` 是实验性参考实现。它依赖 NumPy 和基于 [TurboFEC](https://github.com/ttsou/turbofec) 构建的辅助程序：

```bash
git clone https://github.com/ttsou/turbofec third_party/turbofec
clang -O3 -Ithird_party/turbofec/include -Ithird_party/turbofec/src \
  tools/remove_turbo_soft.c \
  third_party/turbofec/src/turbo_dec.c \
  third_party/turbofec/src/turbo_enc.c \
  third_party/turbofec/src/turbo_rate_match.c \
  -lm -o build/remove_turbo_soft
```

不同平台可能需要调整 SIMD、架构参数以及脚本中启动辅助程序的方式。有效解码必须同时满足：

```text
CRC24A(176-byte transport) == 0
DJI_CRC16(logical payload) == 0
```

有效解码判据以 CRC24A 与 DJI CRC16 同时通过为准。

## 公开数据规范

仓库示例使用合成或脱敏的设备标识与位置。凭据、会话密钥和原始大型采样保存在研究者本地安全环境；第三方代码与固件通过原始来源和许可证引用。发布采样时应同步清理载荷、绝对路径、时间地点及采集元数据中的个人信息。

## 合法与安全使用

本项目用于互操作性研究、频谱分析、接收机开发和经授权的安全研究。使用范围为遵守所在地无线电、隐私、航空和计算机安全法规的被动接收及明确授权测试。

DJI、OcuSync 和相关产品名称属于各自权利人。本项目与 DJI 无隶属或背书关系。

## 完整研究记录

### 证据规则

本项目按以下优先级处理信息：

```text
原始 IQ > 自己的双 CRC 结果 > 原始技术资料 > 公开代码 > 讨论区评论 > 推测
```

“检测到信号”和“解码成功”必须分开：

- ZC/CP/频谱峰只证明候选物理层结构；
- CRC24A 通过证明 176-byte transport 恢复成功；
- DJI CRC16 再通过才证明逻辑包边界和内容一致；
- 加密载荷即使双 CRC 通过，也不代表已经获得明文。

### HackRF 数据约定

HackRF 原始文件是 signed int8、I/Q 交错：

```text
I0 Q0 I1 Q1 ...
2 bytes / complex sample
duration = file_bytes / 2 / sample_rate
```

中心 DC spike 应在检测和频谱统计中去除、notch 或设置 guard。I+jQ 与 I−jQ 约定可能与参考实现相反，应通过 ZC 相关自动选择，而不是硬编码猜测。

#### 20 MS/s 与 15.36 MS/s

文件大小、complex sample 字节数和分析器报告时长可以交叉核对实际采样率。20 MS/s 输入到经典 15.36 MS/s 检测器的正确比率为：

```text
15.36 / 20 = 96 / 125
```

大型文件应分块 polyphase 重采样，并维护滤波器状态与块间 overlap；不应一次性加载约 1 GB IQ。

### O2 金标准物理层

经典 O2 DroneID 的已验证结构：

```text
sample rate       15.36 MS/s
FFT               1024
subcarrier space  15 kHz
active carriers   600（DC excluded）
symbols           9
normal CP         72
long CP           80
symbol index 3    ZC root 600
symbol index 5    ZC root 147
data symbols      1,2,4,6,7,8
```

601 点 Zadoff–Chu 序列生成后删除中间元素，再映射到 DC 两侧的 600 个载波。真实帧长度约 9880 samples，即约 643.2 µs。

### O2 FEC 链

```text
6 QPSK symbols × 600 carriers × 2 bit = 7200 soft bits
→ Gold descramble
→ LTE reverse rate matching, E=7200, RV=0
→ LTE Turbo, K=1408, D=1412
→ 176-byte transport
→ CRC24A
→ variable logical payload
→ DJI CRC16
```

已使用原始 IQ 独立恢复到 CRC24A 与 DJI CRC16 同时为 0。仓库不提供带真实身份和坐标的 payload 或 IQ。

### 扫描与频点经验

在 2.4 GHz 实验中使用过 15 MHz raster：

```text
2399.5 / 2414.5 / 2429.5 / 2444.5 / 2459.5 MHz
```

这些是实验扫描中心，不应描述为所有型号、地区和固件都固定使用的官方频点。单个 HackRF 无法同时覆盖整个频段；驻留时间和重访速度存在直接权衡。

一次 15.36 MS/s、中心 2407.5 MHz 的采样只覆盖约 2399.82–2415.18 MHz。完整判断以 burst 全带宽落入接收窗口为前提；边缘覆盖只适合发现候选能量和部分频谱结构。

### OcuSync 主链路与 DroneID 的区分

O2 与 O4 主链路都观察到 LTE-like numerology：15 kHz、FFT1024、约 72 CP、约 600 active carriers，以及 5 ms / 200 Hz 时间结构。因此：

```text
5 ms periodicity != DroneID 的充分证据
```

必须区分：主图传、control/C2、标准 Wi-Fi/Bluetooth RID 与 DJI DroneID。高占空主链路应使用 CP/ZC、带宽和帧结构联合分类；简单 median+MAD 功率阈值会随整体占空和功率基线变化。

### O4 新发现

在多份 O4 逻辑包中确认了 `AA`、`A7`、`87` 等类型。AA/87 使用 4 字节 hashcode 关联会话。A7 被第三方资料描述为非加密信息包，但本项目不依赖它恢复 87。

实测飞行状态下捕获到 AA 和同 hash 的 87。厂商服务对 AA 返回 16 字节 note 后，87 可完全离线解密。密码学细节见下方“密码学链路”章节。

两份以 20 MS/s 录制的 2.4 GHz IQ 在正确重采样后均找到双 CRC 有效的 87；错误采样率分析曾把 ZC 最大相关压到约 0.16–0.17 并错误显示无帧。

### O4 PHY 边界

捕获到的部分 O4 加密包仍保留经典 9-symbol root600/root147 shell，并可以通过既有 O2 PHY/FEC 链恢复为双 CRC 有效逻辑包。公开讨论还报告过较新的 10-symbol 动态 root 结构：

```text
Q Q Q | ZA ZA | ZB ZB | Q Q Q
```

它含 6 个 QPSK 数据符号，同样对应 7200 bits。该结构目前标记为待端到端验证假设；不同 O4 型号和协议版本应分别识别帧壳。

### AA/87 广播条件

本项目 O4 采集来自 DJI Mini 5 Pro。仅在 GPS/GNSS 定位有效后开始发送 AA 关键材料包；操作者点击启动/起飞后开始形成已验证的 87 动态流。O2/O3 的行为不同：飞行器开机后即发送明文 DroneID 载荷，包括未连接遥控器的状态。

### 密码分析边界

- 标准 SM2 在少量 `AA → note` 已知明密文对下仍保持约 128 位通用攻击强度；
- AES-128 note 的完整密钥空间为 `2^128`；
- 87 中固定明文字段适合作为候选密钥验证器；
- 飞行器侧 SM2 公钥适合确认密钥体系、key ID 与加密调用链；AA 解密使用对应私钥。

应优先研究低熵 note 派生、C1/nonce 复用、固件中的 key ID/公钥及合法取得的离线接收实现。

### 复现实验检查点

1. 由采集命令、文件大小和报告时长交叉核对采样率。
2. 由真实采集命令确认中心频率和增益。
3. 使用 CP、ZC、符号数和双 CRC 联合识别 DroneID。
4. 将 ZC 峰记录为 PHY candidate，将双 CRC 通过记录为 payload decode。
5. 将 CRC 有效加密包标记为 encrypted transport，并保留原始载荷。
6. 将第三方术语标注为资料来源，协议结论由独立样本验证。
7. 公开结果使用脱敏标识、坐标和凭据字段。

### 推荐复现实验输出

每个候选帧至少保存：

```text
candidate.iq
symbols_fd.npy
equalized.npy
llr_7200.npy
descrambled_llr.npy
turbo streams
transport_176.bin
logical_payload.bin
decode.json
```

`decode.json` 应记录采样率、中心频率、帧起点、CP/ZC score、CFO、CRC 结果、逻辑长度和 payload SHA-256。公开前移除绝对路径、时间地点与身份字段。

### 后续工作

- 从更多独立会话验证 AA 的标准 SM2 KDF/C3；
- 定位飞行器固件中的业务公钥和 key ID；
- 研究具备合法离线解析能力的接收设备；
- 为 20→15.36 MS/s 实现带状态的流式重采样；
- 将 10-symbol 动态-root O4+ 检测纳入独立 pipeline；
- 建立不含个人信息的合成包与单元测试集。

## O4 密码学链路

### 1. 已确认的会话关系

AA 是关键材料包，87 是动态遥测包。逻辑包 bytes `6:10` 是 4 字节 `hashcode`。同一会话的 AA 与 87 共享 hashcode。

```text
AA(hash=H) → note K
87(hash=H, nonce=N1) → AES-CTR(K, N1)
87(hash=H, nonce=N2) → AES-CTR(K, N2)
...
```

实测中，一个 note 成功解密同一 hash 下至少 8 个不同 87，序号、时间、坐标和高度连续合理。它不是每包一个密钥，而是会话密钥。会话刷新后旧 note 不再适用。

### 2. 通用逻辑包头

```text
offset  size  含义
0       1     packet_length_minus_3
1       1     message type / subtype
2       4     ASCII marker: CRYP 或 INFP
6       4     hashcode
...     ...   type-specific body
last-2  2     DJI CRC16, little-endian
```

逻辑长度为 `packet[0] + 3`。CRC16 初值为 `0x3692`、反射多项式为 `0x8408`；完整逻辑包计算余数为 0。

### 3. AA 布局

已观察的 AA 头为：

```text
AA 13 43 52 59 50 [hashcode]
```

其中 `43 52 59 50` 是 ASCII `CRYP`。

```text
offset    size  解释
10:74     64    C1 = X || Y，两个 32-byte big-endian 坐标
74:106    32    C3 candidate
106:122   16    C2 candidate；明文长度与 note 一致
122:...   ...   其余协议字段与尾部数据
```

四个独立会话中的 C1 均满足国密 SM2 曲线：

```text
p = FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
a = FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
b = 28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93

y² ≡ x³ + ax + b (mod p)
```

64 + 32 + 16 的长度又与无 `04` 点前缀的 SM2 `C1‖C3‖C2` 完全吻合。因此，“标准 SM2 公钥加密”是高置信结论。严格的最终确认仍需要私钥计算共享点并重算 KDF 与 C3；也存在极小可能是使用 SM2 曲线和同样封装的自定义 ECIES。

标准 SM2 假设下：

```text
S    = d × C1
mask = SM2_KDF(S.x || S.y, 16)
note = C2 XOR mask
C3 ?= SM3(S.x || note || S.y)
```

飞行器侧使用公钥生成 AA，解密侧需要私钥。当前开源实现的边界位于私钥输入：提供有效私钥或等价解密模块后即可验证 KDF 与 C3。

### 4. 87 布局与已验证解密

```text
offset   size       含义
0        1          0x87
1        1          0x10
2:6      4          ASCII "INFP"
6:10     4          hashcode
10:18    8          per-packet nonce
18:20    2          ciphertext length, uint16 little-endian
20:...   variable   ciphertext
last-2   2          DJI CRC16
```

解密参数：

```text
cipher = AES-128-CTR
key    = note                         # 16 bytes
IV     = packet[10:18] || 00×8        # 16 bytes
body   = packet[20 : 20 + uint16_le(packet[18:20])]
```

CTR 模式不提供认证，因此解密后仍要检查固定字段、长度、序号和遥测连续性。外层 DJI CRC16只证明空口逻辑包传输正确，不证明 note 正确。

### 5. 已知明文结构（当前样本）

已验证明文包含：版本、sequence、state、16 字节 SN、经纬度原始值、高度、相对高度、三轴量、yaw、毫秒时间、飞手坐标、返航点坐标、产品类型与可变长度 UUID。

已验证的 109 字节明文使用以下偏移；多字节数值均为小端：

| 明文偏移 | 长度 | 类型 | 实测含义/换算 |
|---:|---:|---|---|
| 0 | 1 | uint8 | message marker，实测 `0x10` |
| 1 | 1 | uint8 | 协议版本 |
| 2 | 2 | uint16 | sequence number |
| 4 | 2 | uint16 | state flags |
| 6 | 16 | ASCII | SN 字段，NUL 补齐 |
| 22 | 4 | int32 | 飞行器经度，弧度 × 10⁷ |
| 26 | 4 | int32 | 飞行器纬度，弧度 × 10⁷ |
| 30 | 2 | int16 | 海拔高度 |
| 32 | 2 | int16 | 相对高度 × 10 |
| 34 | 2 | int16 | X/速度类原始值 |
| 36 | 2 | int16 | Y/速度类原始值 |
| 38 | 2 | int16 | Z/速度类原始值 |
| 40 | 2 | int16 | yaw × 100 度 |
| 42 | 8 | uint64 | Unix 毫秒时间 |
| 50 | 4 | int32 | 飞手纬度，弧度 × 10⁷ |
| 54 | 4 | int32 | 飞手经度，弧度 × 10⁷ |
| 58 | 4 | int32 | 返航点经度，弧度 × 10⁷ |
| 62 | 4 | int32 | 返航点纬度，弧度 × 10⁷ |
| 66 | 1 | uint8 | 产品类型 |
| 67 | 1 | uint8 | UUID 长度 |
| 68 | variable | ASCII | UUID |

经纬度是带符号 32 位弧度定点值：

```text
degrees = raw_i32 / 10_000_000 × 180 / π
```

字段布局可能随型号或协议版本变化，解析器应保留原始明文并对长度做边界检查。

### 6. A3 / 80 的状态

第三方服务资料将 A3/80 描述为与 AA/87 相同的“关键包/动态包”配对。当前完整密码学实测确认集中在 AA→note→87；A3/80 的偏移、IV 和字段仍列为独立样本验证项目。

### 7. 密码分析边界

标准 AES-128 的完整密钥空间和 SM2-256 的通用攻击都具有约 128 位安全强度，直接暴力不可行。更有意义的检查包括：

- note 是否由低熵种子或时间字段派生；
- 不同 AA 是否复用 C1；
- 相同 note 下 87 nonce 是否碰撞；
- 固件是否包含业务公钥、key ID 或离线解密模块；
- 经授权的实现是否遗漏曲线点验证或存在侧信道。

公钥可能存在于飞行器固件、配置区或安全模块中，可用于确认密钥体系和定位实现。AA 解密需要对应私钥；其部署位置更可能是服务器 HSM 或具备离线解析能力的接收设备。

## 可复现测量值与计算过程

本文记录协议结论背后的具体数值，并按采集与处理阶段组织，便于独立复现。设备身份、精确位置、完整加密报文和有效会话密钥均采用脱敏表达。

### 1. IQ 表示与时长计算

HackRF 原始数据是 signed int8 交错 I/Q：

```text
byte 0 = I0
byte 1 = Q0
byte 2 = I1
byte 3 = Q1
...
```

每个 complex sample 占 2 字节：

```text
complex_samples = file_size_bytes / 2
duration_seconds = file_size_bytes / (2 × sample_rate_hz)
```

以下两个 O4 文件由 `hackrf_transfer -s 20000000` 录制：

| 采集中心 | 文件大小 | 按实际 20 MS/s 计算 | 按 15.36 MS/s 解释的表观时长 |
|---:|---:|---:|---:|
| 2429.5 MHz | 740,294,656 B | 18.507366400 s | 24.098133333 s |
| 2444.5 MHz | 974,127,104 B | 24.353177600 s | 31.709866667 s |

两种表观时长的比值正好对应重采样比例：

```text
20.00 / 15.36 = 125 / 96
15.36 / 20.00 = 96 / 125 = 0.768
```

正确处理链为：

```text
HackRF 20 MS/s signed-int8 IQ
  → 去 DC
  → polyphase resample, up=96, down=125
  → 15.36 MS/s complex IQ
  → 经典 ZC / OFDM 检测器
```

### 2. I/Q 实测特征

#### O4 / Mini 5 Pro

| 状态 | 时长 | Mean I | Mean Q | 近似样本标准差 |
|---|---:|---:|---:|---:|
| 电机关闭 | 10.8462 s | -1.208 | -4.311 | 1.84 |
| 电机开启、等待 | 10.3678 s | -1.195 | -4.308 | 10.86 |
| 电机开启、动作 | 8.0740 s | -1.184 | -4.302 | 8.64 |

其他检查结果：

- I/Q 增益不匹配小于 0.01 dB；
- I/Q 相关系数约为 0；
- 未观察到显著 signed-int8 削顶；
- 稳定的非零均值符合 HackRF 中心/DC 偏移特征，相关计算前应去除。

#### O2 / Mini 2

| 状态 | 时长 | Mean I | Mean Q | 近似 I 通道标准差 |
|---|---:|---:|---:|---:|
| 电机关闭 | 6.3402667 s | -1.15047 | -4.31490 | 5.92 |
| 电机开启 | 6.4853333 s | -1.15364 | -4.33045 | 9.064 |
| 电机动作 | 6.5194667 s | -1.15234 | -4.30780 | 8.993 |

未观察到显著削顶。不同状态下 DC 均值近似稳定，而信号活动主要改变方差，因此每个分析窗口应独立减去 complex mean。

### 3. RF 带宽与质心

#### O4 主链路

| 状态 | 近似占用范围 | 99% 带宽 | 质心 |
|---|---|---:|---:|
| 电机开启、等待 | 2403.071–2411.992 MHz | 8.921 MHz | 2408.230 MHz |
| 电机开启、动作 | 2403.057–2411.982 MHz | 8.926 MHz | 2408.007 MHz |

名义信道宽度约为 10 MHz。2402.05 MHz 附近另有约 1.0–1.1 MHz 的窄带特征，主 OFDM 数值统计时已将其排除。

#### O2 主链路

占用范围约为 2403.0–2412.0 MHz，99% 带宽约 8.98 MHz。motor-on 与 action 平均 PSD 的相关系数约为 0.9918。

### 4. 时间结构

#### O4 包络

| 状态 | 强包络分量 | 周期 |
|---|---:|---:|
| 电机关闭 | 400.048 Hz | 2.4997 ms |
| 电机开启、等待 | 200.043 Hz | 4.9989 ms |
| 电机开启、动作 | 200.024 Hz | 4.9994 ms |

等待/动作状态的 5 ms 模板相关约为 0.991。近似一帧可分为 0–3.27 ms 强活动、3.27–4.47 ms 间隔、4.47–5.00 ms 强活动。高于 10 dB 门限的活动比例约为：关闭 18.0%、等待 71.3%、动作 66.5%。

#### O2 包络

| 状态 | 强包络分量 | 高于 10 dB 的活动比例 |
|---|---:|---:|
| 电机关闭 | 499.98 Hz | 25.55% |
| 电机开启 | 199.99 Hz | 77.16% |
| 电机动作 | 200.016 Hz | 77.25% |

O2/O4 共有的 200 Hz / 5 ms 特征首先指向 OcuSync 时间结构家族，具体 DroneID 帧还需要 CP、ZC、符号数和 CRC 联合确认。

### 5. OFDM 参数计算

参考序列使用归一化复相关分数：

```text
score(r, s) = |Σ conj(s[n]) r[n]| / sqrt(Σ|r[n]|² × Σ|s[n]|²)
```

CP 相关与 CFO 使用循环前缀和 useful symbol 的重复样本：

```text
P = Σ conj(x[n]) x[n + NFFT]
cp_score = |P| / sqrt(Σ|x[n]|² × Σ|x[n + NFFT]|²)
cfo_hz = angle(P) × Fs / (2π × NFFT)
```

实现中合并多个 normal-CP symbol 的 P，以获得更稳定的 CFO 估计。

15.36 MS/s 下：

```text
FFT useful duration = 1024 / 15,360,000
                    = 66.6666667 µs

subcarrier spacing = 15,360,000 / 1024
                   = 15,000 Hz

normal symbol duration ≈ (1024 + 72) / 15,360,000
                       ≈ 71.3542 µs
```

#### O4 主链路：20→15.36 MS/s 后

- FFT 候选 960–1088 中 N=1024 明显最优；
- N=1024 CP 相关 99.5 分位约 0.923；
- 最强 CP 相关约 0.992；
- 常见 CP 峰间距约 1095 samples；
- active carriers 约 600–620；
- 倒数时间尺度与占用带宽均符合 15 kHz 子载波间隔。

#### O2 主链路

- N=1024 CP 相关 99.9 分位：关闭 0.9574、开启 0.9813、动作 0.9779；
- 最强相关约 0.994–0.997；
- 常见 CP 间距 1094–1101 samples，主值 1095–1097；
- normal CP 约 72 samples，偶发 long CP 约 80；
- active span 约 605 bins，即 9.075 MHz。

### 6. 经典 O2 DroneID 金标准帧

| 数值 | 实测结果 |
|---|---:|
| 粗 burst 起点 | 1.192375 s |
| 精细 OFDM 起点 | 1.19237793 s |
| 总帧长 | 9,880 samples |
| 计算帧时长 | 643.229 µs |
| fine CFO | 约 +1.106 kHz |
| 分数采样定时修正 | 约 -3.715 samples |
| root-600 相关 | 约 0.928 |
| root-147 相关 | 约 0.843 |
| data symbol 伪 ZC 分数 | 约 0.13–0.14 |
| 连续频谱宽度 | 约 9.70 MHz |
| 99% 带宽 | 约 8.94 MHz |
| 中心偏移 | 约 +26 kHz |

9-symbol 样本数可以直接由 useful symbol 和 CP 求得：

```text
9 × 1024 + (80 + 7×72 + 80) = 9,880 samples
9,880 / 15,360,000 = 0.0006432291667 s
```

### 7. 两个 CRC 计算值

O2 参考解码恢复了 176 字节 transport block，前 173 字节由 CRC24A 保护：

| 校验 | 接收字节/数值 | 独立计算值 | 完整块余数 |
|---|---|---|---:|
| 外层 CRC24A | `34 9F E5` / `0x349FE5` | `0x349FE5` | `0x000000` |
| 内层 DJI CRC16 | `4D E5` 小端 / `0xE54D` | `0xE54D` | `0x0000` |

CRC24A 使用多项式 `0x864CFB`、初始余数为 0。DJI CRC16 使用初值 `0x3692`、反射多项式 `0x8408`。

```text
outer_ok = CRC24A(transport_176) == 0
inner_ok = DJI_CRC16(logical_payload) == 0
decode_ok = outer_ok and inner_ok
```

恢复出的逻辑 payload 长度为 91 字节，即 `payload[0] + 3`。公开测量记录省略其设备身份和位置字段。

### 8. O4 采样率修正结果

两个 20 MS/s 文件直接按 15.36 MS/s 解释时，经典 ZC 最大分数约为 0.166 和 0.177。完成 96/125 重采样后：

| 中心频率 | ZC 配对候选 | 双 CRC 有效逻辑包 | 包类型 | 文件内事件时间 |
|---:|---:|---:|---:|---:|
| 2429.5 MHz | 3 | 1 | `0x87` | 约 15.7836 s |
| 2444.5 MHz | 4 | 1 | `0x87` | 约 21.0137 s |

这证明两份文件包含 DroneID 家族帧，并且初始低相关来自时间尺度不匹配。

### 9. AA / 87 结构数值

#### AA

```text
declared logical length = 0xAA + 3 = 173 bytes
header                  = AA 13 "CRYP"
hashcode                = offsets 6:10，共 4 bytes
C1                      = offsets 10:74，共 64 bytes
C3 candidate            = offsets 74:106，共 32 bytes
C2 candidate            = offsets 106:122，共 16 bytes
SM2 envelope core       = 64 + 32 + 16 = 112 bytes
```

来自 4 个独立会话的 4 个 C1 均通过 SM2 曲线方程验证；C2 长度与同会话服务返回的 16 字节 note 完全一致。

#### 87

```text
declared logical length = 0x87 + 3 = 138 bytes
header                  = 87 10 "INFP"
hashcode                = offsets 6:10，共 4 bytes
nonce                   = offsets 10:18，共 8 bytes
ciphertext length       = offsets 18:20，小端 uint16
observed encrypted body = 已验证样本中为 109 bytes
AES IV                   = nonce8 || 00 00 00 00 00 00 00 00
```

一个 note 成功解密同 hash 会话的 8 个不同 87 包，sequence 分别为 141、262、271、314、348、395、404、443，跨度约 164 秒。其高度位于约 78–99 的连续变化范围，身份字段和参考坐标保持一致。

多包连续性同时验证了密钥、CTR IV 构造、字段偏移、时间推进和会话映射。

### 10. 结论置信度

| 结论 | 置信度 |
|---|---|
| HackRF 字节排列与时长公式 | 已验证 |
| 20→15.36 MS/s 比例 96/125 | 精确计算 |
| O2 FFT1024 / 15 kHz / CP72–80 / 600 carriers | 已验证 |
| O2 9-symbol root600/root147 shell | 已验证 |
| O2 transport 与逻辑载荷 | 两个 CRC 验证 |
| O4 AA/87 逻辑包提取 | 两个 CRC 验证 |
| 87 AES-128-CTR key 与 IV 构造 | 8 个包连续验证 |
| AA C1 位于 SM2 曲线 | 4 个会话验证 |
| AA 每个细节均为标准 SM2 `C1‖C3‖C2` | 强证据，等待私钥验证 |
| A3/80 使用完全相同偏移和密码构造 | 独立验证项目 |

## License

本仓库原创内容使用 [GNU General Public License v3.0](LICENSE)。第三方依赖仍适用其各自许可证。
