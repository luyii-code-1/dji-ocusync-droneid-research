# DJI OcuSync DroneID Research

[English](README.md) | [简体中文](README.zh-CN.md) | [事实与证据](FACTS.zh-CN.md)

基于 HackRF 原始 IQ 的 DJI OcuSync DroneID PHY、逻辑包与密码学链路可复现研究。

**更新于 2026-10-02。** 仓库现在严格区分“本地可复现实测”与“第三方公开确认”。逐条事实、证据等级和精确引用见 [FACTS.zh-CN.md](FACTS.zh-CN.md)。

当前 O4 主结论为：CRYP 中封装的是**随机生成的 AES-128 会话密钥**，使用 SM2 公钥加密；INFP 是使用该会话密钥进行 **AES-128-CTR** 加密的 DroneID 遥测。公开讨论已经给出一份完整参考解密器——只要提供对应的 256-bit SM2 私钥标量即可运行。当前缺口是对应私钥材料/等价 dongle 能力，而不是包格式或 AES 层。

## 已确认结论

对于本仓库在 Mini 5 Pro 上复现、并由公开讨论独立确认的 O4 链路：

```text
飞行器
  随机 AES-128 会话密钥 K
  随机 SM2 临时标量 k
       │
       ├─ C1 = kG
       ├─ S  = kQ              （Q = AeroScope 接收端公钥）
       └─ SM3 KDF 掩码 K
              ↓
         AA / CRYP
              ↓  对应 SM2 私钥标量 d
         会话密钥 K
              ↓
87 / INFP = AES-128-CTR(K, nonce8 || 0x00×8, telemetry)
```

统一术语：

| 实测名称 | 协议角色 |
|---|---|
| `AA`、ASCII `CRYP` | SM2 封装随机 AES 会话密钥的报文 |
| `note` | 16-byte AES 会话密钥 |
| `87`、ASCII `INFP` | AES-CTR 加密动态遥测 |
| `hashcode` / key identifier | 实测中用于关联 CRYP/INFP 的 4-byte 会话标识 |

关键公开确认：

- [CRYP = SM2-wrapped session key；INFP = AES-CTR telemetry](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205)
- [随机 session key + SM2 公钥封装的详细说明](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928617113)
- [需要 SM2 私钥标量的完整 Python 参考解密器](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887)
- [完整事实与证据索引](FACTS.zh-CN.md)

## 当前状态

| 环节 | 状态 | 依据 |
|---|---|---|
| HackRF signed-int8 IQ 输入 | **本地已验证** | 实际录制与回放 |
| 经典 O2 PHY/FEC/CRC | **本地已验证** | [解码器](src/o2_droneid_decode.py)、[Turbo 适配器](tools/remove_turbo_soft.c) |
| O4 AA/CRYP 与 87/INFP 恢复 | **本地已验证** | 双 CRC 有效样本 |
| CRYP 的 C1 位于 SM2 曲线，且符合 `C1‖C3‖C2` | **本地已验证 + 公开确认** | 本地检查 + [协议确认](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205) |
| `note → INFP/87` AES-128-CTR | **本地已验证** | 连续合理遥测 |
| 随机会话密钥 + SM2 封装模型 | **公开确认** | [Issue #1 纠正说明](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928617113) |
| 给定正确 SM2 私钥后的完整解密器 | **已公开** | [参考代码](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |
| 对应 SM2 private scalar | **未公开** | 当前引用资料中没有公开提取结果 |
| 第三方完整离线 O4 解码 | **已有公开声明** | [online/offline resolved](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704941726)、[确认完整遥测](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5705619316) |
| 把 Remote-ID `root_key/CMAC/RIDkey` 当成 O4 DroneID KDF | **已纠正 / 排除** | [Remote ID 纠正](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5929240147)、[DroneID 不使用该机制](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656) |

## 目前真正未公开的部分

算法链已经公开到可以实现的程度。标准路径下完全独立离线解码的实际缺口，是**对应 SM2 私钥标量或等价硬件 oracle**。

当前公开证据包括：

- AeroScope 升级硬件包含带密钥材料的 USB 解密 dongle：[Aerial Defence / Edgesource 安全研究](https://www.aerial-defence.com/security-risks-of-the-aeroscope-upgrade-module-whitepaper/)。
- dongle / TEE 通信路径已有公开安全研究：[Issue #1 资料指针](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928949673)。
- EdwardBlair 将从 dongle 获取密钥材料描述为剩余的关键方向：[评论](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948750307)。

本仓库**不声称 SM2 私钥已经被公开提取**。

同时明确排除此前误区：`root_key → CMAC → RIDkey` 属于 **Remote ID / 遥控器内部遥测保护**，不是 OcuSync DroneID 的 CRYP/INFP 密钥链。详见 [FACTS.zh-CN.md](FACTS.zh-CN.md#3-已纠正remote-id-的-cmac-kdf-不是-ocusync-droneid)。

## 实测机型与发包行为

### DJI Mini 5 Pro / O4

实测行为：

- GPS/GNSS 定位有效后开始出现 CRYP/AA 关键材料包；
- 操作者启动/起飞后开始出现 INFP/87 动态遥测；
- CRYP 与同一会话的 INFP 共享 4 字节 `hashcode`；
- 会话刷新或飞行器重启后，需要对应的新会话密钥。

### O2 与 O3 的边界

不应再把“O2/O3”笼统描述成统一的明文 DroneID 行为。

本仓库经典 O2 样本仍符合已知明文 DroneID 链路；但已经在至少一个 O3 平台——**DJI Inspire 3（悟 3）**——观察到加密 DroneID。因此，“O3 整体均为明文 DroneID”这一旧表述不再成立。

在没有完成逐机型、逐固件交叉验证前，仍应区分“悟 3 O3 已确认存在加密 DroneID”与“悟 3 O3 和 O4 使用完全相同的 CRYP/INFP 密码内部实现”这两个结论。

## 仓库内容

```text
src/o4_packet_tool.py       检查 CRYP/AA，并在已知 note 时解密 INFP/87
src/o2_droneid_decode.py    经典 O2 PHY/FEC 参考解码器
src/droneid_hackrf_scanner.py
                            HackRF 实时/回放扫描器
tools/remove_turbo_soft.c   TurboFEC 适配器
```

## 快速使用

环境要求：Python 3.10+、OpenSSL 命令行。

检查 AA/CRYP：

```bash
python3 src/o4_packet_tool.py '<AA完整Hex>'
```

已知同一会话 16 字节 note 时解密 87/INFP：

```bash
python3 src/o4_packet_tool.py --note '<16-byte-note-hex>' '<87完整Hex>'
```

当前公开工具覆盖逻辑包检查以及“已知会话密钥 → AES 解密”的可复现部分，不包含 DJI 或任何第三方商业实现所持有的私钥材料。

## 会话关系

同一会话的报文共享 hash：

```text
CRYP/AA(hash=H) → session key K

INFP/87(hash=H, nonce=N1) → AES-CTR(K, N1 || 0x00×8)
INFP/87(hash=H, nonce=N2) → AES-CTR(K, N2 || 0x00×8)
INFP/87(hash=H, nonce=N3) → AES-CTR(K, N3 || 0x00×8)
...
```

同一个已恢复 note 已用于连续多个 INFP/87 包，并成功得到连续变化且相互一致的序号、时间、坐标和高度等字段。因此可以确定 `note` 是会话级 AES 密钥，而不是单包密钥。

## 通用逻辑包头

```text
offset  size  含义
0       1     packet_length_minus_3
1       1     message type / subtype
2       4     ASCII 标识（`CRYP`、`INFP` 等）
6       4     hashcode
...     ...   类型相关正文
last-2  2     DJI CRC16，小端
```

逻辑包长度为 `packet[0] + 3`。

DJI CRC16 初始值为 `0x3692`，反射多项式为 `0x8408`。完整有效逻辑包的 CRC 余数为 0。

## CRYP / AA 结构

已观察 AA 包头：

```text
AA 13 43 52 59 50 [hashcode]
      C  R  Y  P
```

关键材料区：

```text
offset    size  解释
10:74     64    C1 = X || Y，两个 32-byte 大端坐标
74:106    32    C3
106:122   16    C2；明文长度与 16-byte session key 一致
122:...   ...   其余协议字段 / 尾部数据
```

多个独立会话中的 C1 均满足标准 SM2 曲线：

```text
p = FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
a = FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
b = 28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93
```

本仓库最初通过 `64 + 32 + 16` 长度关系以及 C1 曲线验证识别出 raw-point SM2 `C1‖C3‖C2`。现在已有第三方公开确认 CRYP 的协议角色就是 **SM2-wrapped session key**。

概念上的标准 SM2 解封过程为：

```text
S    = d × C1
mask = SM2_KDF(S.x || S.y, 16)
note = C2 XOR mask
C3   = SM3(S.x || note || S.y)
```

其中 `d` 为对应私钥。本仓库不提供 `d`。

## INFP / 87 加密

已验证动态遥测使用：

```text
cipher = AES-128-CTR
key    = note
IV     = nonce8 || 0x00×8
```

给定正确的同会话 note，密文能够解出稳定字段结构与连续合理的 DroneID 遥测。

## PHY / FEC 基线

### 经典 O2 帧

```text
sample rate       15.36 MS/s
FFT               1024
subcarrier space  15 kHz
active carriers   600，DC excluded
symbols           9
normal CP         72
long CP           80
symbol index 3    ZC root 600
symbol index 5    ZC root 147
data symbols      1,2,4,6,7,8
```

FEC 链：

```text
6 QPSK symbols × 600 carriers × 2 bits = 7200 soft bits
→ Gold descramble
→ LTE reverse rate matching, E=7200, RV=0
→ LTE Turbo, K=1408, D=1412
→ 176-byte transport
→ CRC24A
→ logical payload
→ DJI CRC16
```

只有 CRC24A 与 DJI CRC16 同时通过，才视为有效逻辑包恢复。

### O4 PHY 边界

部分实测 O4 加密包仍保留经典 9-symbol root600/root147 shell，并能通过既有 O2 PHY/FEC 链恢复为双 CRC 有效的加密逻辑包。

公开讨论还出现过新的 10-symbol 动态 root 结构：

```text
Q Q Q | ZA ZA | ZB ZB | Q Q Q
```

在形成逐机型/逐固件的双 CRC 端到端证据前，不应把该结构描述成所有 O4/O4+ 的统一格式。

## 采样率要求

HackRF 原始文件为 signed-int8 I/Q 交错：

```text
I0 Q0 I1 Q1 ...
2 bytes / complex sample
```

20 MS/s 输入经典 15.36 MS/s 检测器时应使用：

```text
20.00 MS/s × 96 / 125 = 15.36 MS/s
```

错误采样率会同时影响 ZC 时间尺度、CP/FFT 窗口、CFO 和后续 CRC，因此采样率一致性属于强制验证条件。

## 证据规则

本项目采用以下证据优先级：

```text
原始 IQ
> 本地可复现双 CRC
> 本地可复现明文遥测
> 独立公开协议确认
> 公开代码
> 讨论区声明
> 假设
```

因此：

- 能量峰不等于 DroneID；
- ZC/CP 命中只表示 PHY 候选；
- CRC24A 证明 transport block 恢复；
- DJI CRC16 证明逻辑包边界和内容一致；
- 双 CRC 有效的加密包仍然是密文；
- 第三方声称拥有离线解码器可以证明实现存在，但不能替代公开可复现的方法。

## 复现实验检查单

1. 记录真实采样率、中心频率和增益。
2. 通过文件大小和 complex-sample 格式复核采样时长。
3. 使用 CP/ZC 和时序定位候选帧。
4. 必须同时通过 CRC24A 与 DJI CRC16。
5. 保留原始密文与 session hash。
6. INFP/87 实验应记录 nonce 与 note 的来源。
7. 发布前清理真实序列号、操作者/Home 坐标、时间地点和其他识别信息。

建议保存中间产物：

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

## 当前研究重点

- 在 Air 3/3S、Mini 4 Pro、Avata 2、Mavic 4 Pro、Inspire 3 等 O3/O4 平台上交叉验证 CRYP/INFP；
- 对比不同固件代际的 key ID 与公钥层级；
- 确认悟 3 O3 是否使用与 O4 完全相同的 CRYP/INFP 密码链，还是仅采用相关的加密 transport；
- 以双 CRC 有效样本完成新版 O4/O4+ PHY 的端到端验证；
- 在不公开受保护凭据的前提下研究合法取得的离线接收机/商业模块接口；
- 扩充合成测试和脱敏的跨机型测试向量。

## 公开与隐私

示例应使用合成或脱敏的设备标识与位置。不要公开私有服务凭据、会话秘密、真实序列号、精确操作者/Home 坐标或可能识别个人的采集元数据。

## 合法与安全使用

本项目用于互操作性研究、频谱分析、接收机开发和经授权的安全研究。使用范围应限制在遵守所在地无线电、隐私、航空和计算机安全法规的被动接收与明确授权测试。

DJI、OcuSync、AeroScope 及相关产品名称属于各自权利人。本项目与 DJI 或文中第三方无隶属、合作或背书关系。

## License

见 [LICENSE](LICENSE)。
