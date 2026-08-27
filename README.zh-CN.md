# DJI OcuSync DroneID Research

[English](README.md) | [简体中文](README.zh-CN.md)

基于 HackRF 原始 IQ 的 DJI OcuSync O2/O4 DroneID 可复现实验记录与工具。

本仓库整理了截至 **2026-08-27** 已由原始采样、CRC 和连续遥测共同验证的结论。研究重点是接收链、物理层、包结构与密码学封装，并清晰标注已验证范围与待研究步骤。

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
docs/RESEARCH_NOTES.md       英文研究记录
docs/RESEARCH_NOTES.zh-CN.md 中文研究记录
docs/O4_CRYPTO_CHAIN.md      英文密码学链路
docs/O4_CRYPTO_CHAIN.zh-CN.md
                            中文密码学链路
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

## License

本仓库原创内容使用 [GNU General Public License v3.0](LICENSE)。第三方依赖仍适用其各自许可证。
