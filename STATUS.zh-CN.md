# DJI DroneID 研究进展总览 —— 2026 年 10 月 30 日

[简体中文](STATUS.zh-CN.md) | [English](STATUS.md) | [事实索引](FACTS.zh-CN.md) | [仓库首页](README.zh-CN.md)

**本项目公开介绍的主要解密路线是方法二：研究飞行器会话密钥的可预测性。** 研究方报告已完成内部验证，认为具备推广价值；完整实现及跨机型证据尚未发表。本文区分仓库已复现内容、公开文献和研究方尚未公开的结果。

## 一、研究进度

| 环节 | 截至 2026-10-30 的状态 | 依据与限制 |
|---|---|---|
| 经典 v2/O2 DroneID PHY/FEC/CRC | **REPO-REPRODUCED** | [O2 解码器](src/o2_droneid_decode.py)、[Turbo 适配器](tools/remove_turbo_soft.c)；属于历史 **9-symbol** 基线 |
| O4 CRYP、INFP-10/INFP-11、SM2 与 AES-CTR | **PUBLIC-SPEC + 本地包结构观察** | [EdwardBlair 新规范](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/README_CN.md)、[参考实现](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/droneid.py)、[本地包工具](src/o4_packet_tool.py) |
| 新一代 v3 DroneID RF/PHY | **规范公开，尚未集成到本仓库旧版扫描器** | [RF_PHY_CN.md](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY_CN.md)：**8-symbol**、173-byte payload + CRC24A、15.36 MS/s；不能当作旧 O2 的 9-symbol 格式 |
| 使用**真实 AeroScope dongle** 的 O4 完整解密 | **第三方公开演示 + 作者公开报告** | [King-Of-Knights 演示日志](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456)、[仓库作者称基于其研究完成硬件辅助离线解码](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078335828)；完整 USB 命令协议/程序未作为公开可复现成果提供 |
| **方法二：会话密钥可预测性（主要公开方向）** | **研究方内部确认；尚不可公开复现** | 研究方报告，部分实现的 `K` 存在可预测成分；机型、固件范围和实现细节尚未公布 |
| 真正的接收端 SM2 私钥标量 `d` | **OPEN** | 本仓库没有真实私钥；[公开规范的 keys 目录只有测试用 dummy key](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454/keys)；dongle 可解封 CRYP 不能推出 `d` 已经被导出 |
| 不使用 dongle 的公开可复现解密器 | **OPEN** | 方法二目前未发布独立可复测的程序；标准 SM2 参考实现需要有效密钥 |
| O4 起转瞬间可能出现明文包 | **争议中 / 缺可复现实测** | [Issue #3：Mavic 4 Pro 机主声明](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3#issuecomment-6459214434)；[EdwardBlair 要求提供具体固件版本](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3#issuecomment-6459273901)；不得推广成 O4 普遍明文 |

## 二、方法二的研究结论

之前讨论的第一种方案是从硬件中提取长期 SM2 私钥。**对外公开介绍的解密方向应以第二种方案为主**：研究 DroneID 会话密钥 `K` 中可能存在的固定、可预测部分及剩余字节的随机性。

研究方于 2026 年 10 月 30 日报告，该方案已在内部确认具备推广价值。这涉及具体实现的密钥生成方式，不是破解 SM2 或 AES 算法。公开协议仍以随机 AES-128 密钥为标准模型。

**目前公开的是方法和研究结论的概述，不是完整可复现的解密程序。** 仓库不提供敏感参数、真实密钥或原始会话数据；适用设备与固件范围尚待公开验证。飞行器的 `K` 与 AeroScope 主机和 dongle 之间的通信密钥不同。

## 三、相关公开研究

[Issue #1 的硬件辅助解密演示](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456)涉及真实 dongle 解封 CRYP，不等于方法二，也没有公开独立复现程序。

[Edgesource 2024 年白皮书](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)记录了升级模块的硬件和通信流程。本文不再包含私人聊天、人物对应关系或未经公开许可的硬件图像。

## 四、协议基线

```text
飞行器：
  按公开协议随机生成的 16-byte AES session key K
       ├─ key_id = SHA-256(K)[0:4]
       ├─ CRYP：SM2_Encrypt(Q, K) → C1 || C3 || C2
       ├─ CRYP auxiliary：AES-128-CTR
       └─ INFP-10 / INFP-11：AES-128-CTR

有合法接收端私钥 d：
  SM2 shared point → SM3 KDF / C3 验证 → K
  SHA-256(K)[0:4] == key_id
  解密 CRYP auxiliary 与相应 INFP

使用真实硬件的离线接收：
  CRYP → AeroScope dongle → 16-byte K → INFP 明文
  （长期私钥 d 留在硬件内部；host↔dongle 通信密钥另算）
```

来源：[最新公开 O4 协议规范](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/README_CN.md)、[仅使用**虚构测试密钥**进行完整往返的 EXAMPLE.md](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/EXAMPLE.md)、[Edgesource 白皮书](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)。

**必须更正 TheOldCode 线索：** 其最初在 [proto17 #63](https://github.com/proto17/dji_droneid/issues/63#issuecomment-6057095721) 声称能提供 O4 key，后来在 [本仓库 Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6075832628) 明确表示**只有在线解密服务的 key，拿不到真实 SM2 私钥**。不能再将此引用作为“私钥可能已提取”的证据。

**Remote ID 与 DroneID 不同：** 此前的 `root_key → CMAC → RIDkey` 是 DJI 内部 Remote ID 相关机制，**不适用 OcuSync DroneID 的 CRYP/INFP**。[纠正来源](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656)。

## 五、v3 RF/PHY 与旧扫描器的区别

EdwardBlair 的 [dji-droneid-spec](https://github.com/EdwardBlair/dji-droneid-spec)（2026-10-22，commit `55bb886`）已将新一代 **v3 DroneID** 射频与包格式公开到可写参考接收器的程度：

- v3 规范列出**七个中心频点（MHz）**：**2414.5、2429.5、2444.5、5756.5、5776.5、5796.5、5816.5**，**不包括 2459.5 MHz**。这与早期讨论列出的“4+4 频点”有差异，作者也 [专门澄清](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6490897000)；旧款飞机可能有其他列表。
- 递增 8-bit publication counter `c`，按 `r=(c+255)%256`，`i=(r+6)%7`，从 `[2429.5, 2444.5, 5756.5, 5776.5, 5796.5, 5816.5, 2414.5]` 中选择下一频道。每次 640 ms；周期 **256×0.640s = 163.84s**。**真实查找表现在已经公开**，以前“暂未公开查找表”的表述过时。
- **8 个 OFDM symbol**，15.36 MS/s、FFT 1024、600 有效载波、6 个 QPSK 数据符号，symbol 2 为 ZC600、symbol 4 为 ZC147、共 **8784 个 complex sample**；173-byte transport payload 与 CRC24A。[射频/PHY 规范](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY_CN.md)。
- 本仓库的 [HackRF scanner](src/droneid_hackrf_scanner.py) 仍然基于**旧 9-symbol 参考 shell**，有 `baseline / issue2 / paper2022` 三套频点列表。它**没有**实现 v3 8-symbol 物理层，也没有实现新规范的相位跟踪。不能因为“听到了某一频道”就宣称跑通新 v3 接收器。
- EdwardBlair 报告该调度已在 **Air 3S、Avata 2、Neo、Neo 2、Mavic 3 Thermal** 上验证；这属于他的**公开测试声明**，本仓库尚未逐机型复现。[来源](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078283920)。
- 最新公开 v3 列表不包含 5.2 GHz；区域/固件可能性的讨论不能被写成“5.2 GHz 已实际出现”。[来源](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078283920)。

注意：旧 O2 9-symbol 双 CRC 有效样本，与新 v3 8-symbol 格式**必须分别验证**。不能仅凭名称 O2/O3/O4 就直接认定抓到的所有数据都采用统一 PHY。

## 六、证据与下一步

- [st2260136-gif](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6478170923) 报告检查了 **119 个**公开的传输块（12 CRYP、93 INFP-10、14 INFP-11），全部双 CRC 有效，关联同一 key ID；**他在同一条评论中明确没有解开真实会话**，所以不能用来证明真实 SM2 私钥已获得。
- 公开协议仓库提供 synthetic/dummy key 往返测试和解析器，能够验证**算法互操作性**；不代表已经具有真实 AeroScope 私钥。[测试目录](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454/tests)。
- 方法二的后续公开材料应使用脱敏统计、机型与固件范围、合成测试用例，避免公开真实会话密钥和敏感轨迹。
- 硬件逆向保留为独立课题，不再作为本项目对外介绍的主要解密路径。
- **不要提交**真实私钥、在线服务密钥、设备认证凭据、敏感航迹、私人聊天截图及未经同意的 X 光原图。

## 主要来源

[本仓库 Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1) · [Issue #2](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/2) · [Issue #3](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3) · [EdwardBlair 新协议规范](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454) · [proto17 #60](https://github.com/proto17/dji_droneid/issues/60) · [Edgesource 白皮书](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)
