# O2 / O4 DroneID 研究笔记

[English](RESEARCH_NOTES.md) | [简体中文](RESEARCH_NOTES.zh-CN.md)

逐采集文件的 IQ 统计、时间参数、ZC 分数以及 CRC 接收值/计算值见 [MEASUREMENTS.zh-CN.md](MEASUREMENTS.zh-CN.md)。

## 证据规则

本项目按以下优先级处理信息：

```text
原始 IQ > 自己的双 CRC 结果 > 原始技术资料 > 公开代码 > 讨论区评论 > 推测
```

“检测到信号”和“解码成功”必须分开：

- ZC/CP/频谱峰只证明候选物理层结构；
- CRC24A 通过证明 176-byte transport 恢复成功；
- DJI CRC16 再通过才证明逻辑包边界和内容一致；
- 加密载荷即使双 CRC 通过，也不代表已经获得明文。

## HackRF 数据约定

HackRF 原始文件是 signed int8、I/Q 交错：

```text
I0 Q0 I1 Q1 ...
2 bytes / complex sample
duration = file_bytes / 2 / sample_rate
```

中心 DC spike 应在检测和频谱统计中去除、notch 或设置 guard。I+jQ 与 I−jQ 约定可能与参考实现相反，应通过 ZC 相关自动选择，而不是硬编码猜测。

### 20 MS/s 与 15.36 MS/s

文件大小、complex sample 字节数和分析器报告时长可以交叉核对实际采样率。20 MS/s 输入到经典 15.36 MS/s 检测器的正确比率为：

```text
15.36 / 20 = 96 / 125
```

大型文件应分块 polyphase 重采样，并维护滤波器状态与块间 overlap；不应一次性加载约 1 GB IQ。

## O2 金标准物理层

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

## O2 FEC 链

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

## 扫描与频点经验

在 2.4 GHz 实验中使用过 15 MHz raster：

```text
2399.5 / 2414.5 / 2429.5 / 2444.5 / 2459.5 MHz
```

这些是实验扫描中心，不应描述为所有型号、地区和固件都固定使用的官方频点。单个 HackRF 无法同时覆盖整个频段；驻留时间和重访速度存在直接权衡。

一次 15.36 MS/s、中心 2407.5 MHz 的采样只覆盖约 2399.82–2415.18 MHz。完整判断以 burst 全带宽落入接收窗口为前提；边缘覆盖只适合发现候选能量和部分频谱结构。

## OcuSync 主链路与 DroneID 的区分

O2 与 O4 主链路都观察到 LTE-like numerology：15 kHz、FFT1024、约 72 CP、约 600 active carriers，以及 5 ms / 200 Hz 时间结构。因此：

```text
5 ms periodicity != DroneID 的充分证据
```

必须区分：主图传、control/C2、标准 Wi-Fi/Bluetooth RID 与 DJI DroneID。高占空主链路应使用 CP/ZC、带宽和帧结构联合分类；简单 median+MAD 功率阈值会随整体占空和功率基线变化。

## O4 新发现

在多份 O4 逻辑包中确认了 `AA`、`A7`、`87` 等类型。AA/87 使用 4 字节 hashcode 关联会话。A7 被第三方资料描述为非加密信息包，但本项目不依赖它恢复 87。

实测飞行状态下捕获到 AA 和同 hash 的 87。厂商服务对 AA 返回 16 字节 note 后，87 可完全离线解密。密码学细节见 [O4_CRYPTO_CHAIN.zh-CN.md](O4_CRYPTO_CHAIN.zh-CN.md)。

两份以 20 MS/s 录制的 2.4 GHz IQ 在正确重采样后均找到双 CRC 有效的 87；错误采样率分析曾把 ZC 最大相关压到约 0.16–0.17 并错误显示无帧。

## O4 PHY 边界

捕获到的部分 O4 加密包仍保留经典 9-symbol root600/root147 shell，并可以通过既有 O2 PHY/FEC 链恢复为双 CRC 有效逻辑包。公开讨论还报告过较新的 10-symbol 动态 root 结构：

```text
Q Q Q | ZA ZA | ZB ZB | Q Q Q
```

它含 6 个 QPSK 数据符号，同样对应 7200 bits。该结构目前标记为待端到端验证假设；不同 O4 型号和协议版本应分别识别帧壳。

## AA/87 广播条件

实测与第三方服务说明都提示，不同型号行为不同：部分型号室内连接即可发送关键包；较新型号可能需要室外定位并进入飞行状态才发送有效 AA/87。该结论具有型号和固件依赖，不应泛化为全部 OcuSync 设备。

## 密码分析边界

- 标准 SM2 在少量 `AA → note` 已知明密文对下仍保持约 128 位通用攻击强度；
- AES-128 note 的完整密钥空间为 `2^128`；
- 87 中固定明文字段适合作为候选密钥验证器；
- 飞行器侧 SM2 公钥适合确认密钥体系、key ID 与加密调用链；AA 解密使用对应私钥。

应优先研究低熵 note 派生、C1/nonce 复用、固件中的 key ID/公钥及合法取得的离线接收实现。

## 复现实验检查点

1. 由采集命令、文件大小和报告时长交叉核对采样率。
2. 由真实采集命令确认中心频率和增益。
3. 使用 CP、ZC、符号数和双 CRC 联合识别 DroneID。
4. 将 ZC 峰记录为 PHY candidate，将双 CRC 通过记录为 payload decode。
5. 将 CRC 有效加密包标记为 encrypted transport，并保留原始载荷。
6. 将第三方术语标注为资料来源，协议结论由独立样本验证。
7. 公开结果使用脱敏标识、坐标和凭据字段。

## 推荐复现实验输出

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

## 后续工作

- 从更多独立会话验证 AA 的标准 SM2 KDF/C3；
- 定位飞行器固件中的业务公钥和 key ID；
- 研究具备合法离线解析能力的接收设备；
- 为 20→15.36 MS/s 实现带状态的流式重采样；
- 将 10-symbol 动态-root O4+ 检测纳入独立 pipeline；
- 建立不含个人信息的合成包与单元测试集。
