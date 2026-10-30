# DJI DroneID 研究进展总览 —— 2026 年 10 月 30 日

[简体中文](STATUS.zh-CN.md) | [English](STATUS.md) | [事实索引](FACTS.zh-CN.md) | [仓库首页](README.zh-CN.md)

这是带证据分级的**阶段性研究记录**，**不代表 AeroScope 长期 SM2 私钥已经提取成功**。综合仓库可复现实验、GitHub 公开讨论，以及仓库作者在其他对话中说明的非公开硬件进度。区分以下等级：`REPO-REPRODUCED`（仓库代码/实测）、`PUBLIC-SPEC`（公开规范与实现）、`PUBLIC-REPORT`（公开第三方报告）、`OWNER-REPORTED / PRIVATE`（作者私下说明，仓库尚不能独立复核）、`OPEN`（未解决）。私人截图或聊天内容不能自动当成独立验证。

## 一、当前总进度

| 环节 | 截至 2026-10-30 的状态 | 依据与限制 |
|---|---|---|
| 经典 v2/O2 DroneID PHY/FEC/CRC | **REPO-REPRODUCED** | [O2 解码器](src/o2_droneid_decode.py)、[Turbo 适配器](tools/remove_turbo_soft.c)；属于历史 **9-symbol** 基线 |
| O4 CRYP、INFP-10/INFP-11、SM2 与 AES-CTR | **PUBLIC-SPEC + 本地包结构观察** | [EdwardBlair 新规范](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/README_CN.md)、[参考实现](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/droneid.py)、[本地包工具](src/o4_packet_tool.py) |
| 新一代 v3 DroneID RF/PHY | **规范公开，尚未集成到本仓库旧版扫描器** | [RF_PHY_CN.md](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY_CN.md)：**8-symbol**、173-byte payload + CRC24A、15.36 MS/s；不能当作旧 O2 的 9-symbol 格式 |
| 使用**真实 AeroScope dongle** 的 O4 完整解密 | **第三方公开演示 + 作者公开报告** | [King-Of-Knights 演示日志](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456)、[仓库作者称基于其研究完成硬件辅助离线解码](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078335828)；完整 USB 命令协议/程序未作为公开可复现成果提供 |
| AeroScope 主机 ↔ dongle 交互认证/模拟 | **OWNER-REPORTED / PRIVATE** | 作者在其他对话中报告已完成通信模拟/通行；不等于完全软件仿真密码芯片，也不等于已取得硬件内部私钥 |
| dongle X 光扫描分析 | **OWNER-REPORTED / PRIVATE** | 作者报告已完成；相关截图中标为 **#4** 的区域曾被推测为 COB/裸片、键合线结构，**不是**芯片型号、存储位置或私钥所在位置的确认；原始 X 光数据尚未在本仓库发表 |
| 拆芯片/开封/侵入式提取 | **OPEN / 下一阶段** | 此前描述为下一步工作，**没有可公开核查的已完成开封提取结果** |
| 真正的接收端 SM2 私钥标量 `d` | **OPEN** | 本仓库没有真实私钥；[公开规范的 keys 目录只有测试用 dummy key](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454/keys)；dongle 可解封 CRYP 不能推出 `d` 已经被导出 |
| 完全不使用 dongle、公开可复现的真实 O4 解密 | **OPEN** | 合成 SM2/AES 测试只说明算法正确，不说明真实私钥已获得 |
| O4 起转瞬间可能出现明文包 | **争议中 / 缺可复现实测** | [Issue #3：Mavic 4 Pro 机主声明](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3#issuecomment-6459214434)；[EdwardBlair 要求提供具体固件版本](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3#issuecomment-6459273901)；不得推广成 O4 普遍明文 |

## 二、私人聊天对象与实验归属

仓库作者已明确：**以前聊天截图中的对方就是 GitHub 用户 [King-Of-Knights](https://github.com/King-Of-Knights)**。这只是聊天对象的账号对应关系，**不能把 King-Of-Knights 与仓库作者视为同一人**，也不等于私聊截图自动通过第三方真实性鉴定。

- **King-Of-Knights 的公开演示：** 他在 [Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456) 贴出控制台结果，表明调用真实 AeroScope dongle 将 CRYP 解封为 **16-byte AES session key**，再解密同会话 INFP。这属于**依赖硬件的离线解密**，不是公布 **256-bit SM2 长期私钥**。
- **作者一侧的私下进度：** 作者在其他对话中报告已完成 dongle 主机侧交互模拟和 X 光分析，拆芯片仍是待做环节。但目前材料不足以明确是合作中的哪一位亲自执行每项操作；因此只将其写为**作者报告的合作研究进度**，不能擅自归功于某个具体参与者。
- **私聊里的所谓“密钥”：** 曾讨论过一段 **128 个十六进制字符（约 64 字节）** 的数据。其**长度与结构**对应 SM2 **公钥点 `Qx || Qy`（32+32 字节）**，**不能据此认定**拿到 32 字节 SM2 **私钥标量 `d`**。即便椭圆曲线方程校验通过，也不能直接证明它属于实际 AeroScope 接收端。本仓库不公开私聊内容、原始 hex、芯片图、人员隐私或未经确认的提取成果。

另据 [Edgesource 2024 年白皮书](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)，2024 年已有实体拆机、USB Hub/处理器分离、主机与 dongle 分别认证及建立加密传输会话的公开研究。**不能把旧白皮书的图片自动算作 King-Of-Knights 于 2026 年的新拆机成果**；该白皮书也未证明内部一定采用 TEE。

## 三、当前真正跑通的密码链

```text
飞行器：
  随机 16-byte AES session key K
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

## 四、2026-10 新公开 PHY 与跳频规范：旧数据不可直接套用

EdwardBlair 的 [dji-droneid-spec](https://github.com/EdwardBlair/dji-droneid-spec)（2026-10-22，commit `55bb886`）已将新一代 **v3 DroneID** 射频与包格式公开到可写参考接收器的程度：

- v3 规范列出**七个中心频点（MHz）**：**2414.5、2429.5、2444.5、5756.5、5776.5、5796.5、5816.5**，**不包括 2459.5 MHz**。这与早期讨论列出的“4+4 频点”有差异，作者也 [专门澄清](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6490897000)；旧款飞机可能有其他列表。
- 递增 8-bit publication counter `c`，按 `r=(c+255)%256`，`i=(r+6)%7`，从 `[2429.5, 2444.5, 5756.5, 5776.5, 5796.5, 5816.5, 2414.5]` 中选择下一频道。每次 640 ms；周期 **256×0.640s = 163.84s**。**真实查找表现在已经公开**，以前“暂未公开查找表”的表述过时。
- **8 个 OFDM symbol**，15.36 MS/s、FFT 1024、600 有效载波、6 个 QPSK 数据符号，symbol 2 为 ZC600、symbol 4 为 ZC147、共 **8784 个 complex sample**；173-byte transport payload 与 CRC24A。[射频/PHY 规范](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY_CN.md)。
- 本仓库的 [HackRF scanner](src/droneid_hackrf_scanner.py) 仍然基于**旧 9-symbol 参考 shell**，有 `baseline / issue2 / paper2022` 三套频点列表。它**没有**实现 v3 8-symbol 物理层，也没有实现新规范的相位跟踪。不能因为“听到了某一频道”就宣称跑通新 v3 接收器。
- EdwardBlair 报告该调度已在 **Air 3S、Avata 2、Neo、Neo 2、Mavic 3 Thermal** 上验证；这属于他的**公开测试声明**，本仓库尚未逐机型复现。[来源](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078283920)。
- 最新公开 v3 列表不包含 5.2 GHz；区域/固件可能性的讨论不能被写成“5.2 GHz 已实际出现”。[来源](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078283920)。

注意：旧 O2 9-symbol 双 CRC 有效样本，与新 v3 8-symbol 格式**必须分别验证**。不能仅凭名称 O2/O3/O4 就直接认定抓到的所有数据都采用统一 PHY。

## 五、证据与下一步

- [st2260136-gif](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6478170923) 报告检查了 **119 个**公开的传输块（12 CRYP、93 INFP-10、14 INFP-11），全部双 CRC 有效，关联同一 key ID；**他在同一条评论中明确没有解开真实会话**，所以不能用来证明真实 SM2 私钥已获得。
- 公开协议仓库提供 synthetic/dummy key 往返测试和解析器，能够验证**算法互操作性**；不代表已经具有真实 AeroScope 私钥。[测试目录](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454/tests)。
- 真实会话的后续可复核资料应包含：完整 CRYP、至少两条同会话 INFP、FEC+CRC 校验结果、**经授权使用的 16-byte session key**、机型/固件、隐私安全的对照飞行日志；不需要公开长期 SM2 私钥。
- 硬件研究真正需要形成的下一项**公开证据**是合法授权取得的芯片型号/裸片或存储分析结果；单凭 X 光定位不到私钥。如果能公开可复现的主机侧 dongle 调用程序，也可以独立确认**硬件辅助离线解密**，不需要导出私钥。
- **不要提交**真实私钥、在线服务密钥、设备认证凭据、敏感航迹、私人聊天截图及未经同意的 X 光原图。

## 主要来源

[本仓库 Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1) · [Issue #2](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/2) · [Issue #3](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3) · [EdwardBlair 新协议规范](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454) · [proto17 #60](https://github.com/proto17/dji_droneid/issues/60) · [Edgesource 白皮书](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)
