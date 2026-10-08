# DJI OcuSync DroneID —— 事实与证据索引

[English](FACTS.md) | [简体中文](FACTS.zh-CN.md)

**最后核对：2026-10-08**

本文把当前信息严格分成：**本仓库可复现实测、第三方公开确认、第三方实现声明、已纠正/排除的路径、仍未解决的问题**。GitHub 评论中的公开说法不会自动等同于本仓库已经独立复现。

## 证据等级

- **LOCAL-VERIFIED / 本地已验证**：由本仓库原始 IQ、CRC、已知密钥解密或代码直接复现。
- **PUBLIC-CONFIRMED / 公开确认**：有独立公开技术讨论明确确认，且与本地证据一致。
- **PUBLIC-CLAIM / 公开声明**：第三方声称已有实现，但实现、密钥或完整测试向量未公开。
- **OBSERVED-NOT-UNIVERSAL / 局部观察**：仅针对特定机型/固件，不能外推到整个协议代际。
- **CORRECTED / 已纠正**：早期解释后来被明确否定或被限定为另一套协议。
- **OPEN / 未解决**：公开资料尚未解决。

## 1. O4 包结构与密码链

| 事实 | 状态 | 证据 |
|---|---|---|
| 本项目观察到 O4 逻辑包中的 `AA/CRYP` 与 `87/INFP`；同一会话的包共享 4 字节会话标识/hash。 | **本地已验证** | [本地 O4 工具](src/o4_packet_tool.py)、[交叉验证 Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1) |
| `CRYP` 携带经 SM2 封装的 AES 会话密钥；`INFP` 携带 AES-CTR 加密遥测。 | **本地已验证 + 公开确认** | [EdwardBlair 的独立确认](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205) |
| 飞行器随机生成 128-bit AES 会话密钥，并随机选择 SM2 临时标量 `k`，使用 AeroScope 接收端公钥 `Q` 计算 `C1=kG` 与共享点 `S=kQ`，再使用 SM3 KDF 将会话密钥封装进 CRYP。 | **公开确认** | [详细纠正说明](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928617113) |
| CRYP 中存在标准 SM2 兼容的 `C1 || C3 || C2`。本仓库样本表现为 64-byte raw EC point + 32-byte C3 + 16-byte C2。 | **本地已验证 + 公开确认** | [本地实现](src/o4_packet_tool.py)、[协议确认](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205) |
| INFP 使用 AES-128-CTR。本仓库样本中 IV 为 `nonce8 || 0x00*8`。 | **本地已验证** | [本地实现](src/o4_packet_tool.py)、[测试](tests/test_o4_packet_tool.py) |
| 同一个恢复出的会话密钥可以连续解密多个同会话 INFP，并得到连续、合理的遥测。 | **本地已验证** | [项目公开更新](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5636317132) |
| Issue #1 已公开一份完整 Python 参考实现，可执行 `SM2 private scalar -> CRYP session key -> INFP plaintext`。 | **公开确认** | [EdwardBlair 发布的参考实现](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |
| 该参考实现要求 32-byte / 256-bit SM2 private scalar，并在解密 INFP 前验证 C3 和 4-byte key identifier。 | **公开确认** | [同一参考实现](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |

当前密码链：

```text
飞行器：
  随机 AES-128 会话密钥 K
  随机 SM2 标量 k
  C1 = kG
  S  = kQ
  mask = SM3-KDF(S)
  CRYP = SM2_Encrypt(Q, K)

接收端：
  S = dC1
  K = SM2_Unwrap(d, CRYP)
  INFP 明文 = AES-128-CTR(K, nonce8 || 0x00*8, ciphertext)
```

其中 `Q` 是 AeroScope/接收端公钥，`d` 是对应 SM2 私钥标量。

## 2. 关于密钥：已经公开什么、仍缺什么

| 事实 | 状态 | 证据 |
|---|---|---|
| 目前协议与解密算法已经公开到“只要拥有正确 SM2 私钥即可实现完整解码”的程度。 | **公开确认** | [完整参考解密器](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |
| 对应 SM2 私钥本身没有在本仓库或上述公开讨论中发布。 | **未解决** | [Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1) |
| AeroScope 升级硬件包含 USB 解密 dongle，公开安全研究称其中包含密钥。 | **公开确认** | [Aerial Defence / Edgesource 白皮书页面](https://www.aerial-defence.com/security-risks-of-the-aeroscope-upgrade-module-whitepaper/) |
| 最新公开讨论将“从 dongle 获得密钥材料”指向为独立完整实现剩余的关键方向。 | **公开声明** | [EdwardBlair：material extraction from the dongle](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948750307) |
| 2024 年白皮书描述了 AeroScope 与 dongle 的认证、通信会话密钥和 CRYP 解封流程；**没有证明 dongle 内部采用 TEE**。 | **公开确认（文献描述）** | [Edgesource 白皮书第 10–12 页](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)、[Issue #1 资料指针](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928949673) |

本仓库**不声称 SM2 私钥已经被公开提取**。

## 2a. AeroScope 升级模块：拆解证据及两种会话密钥

**2024 年已有的硬件拆解，并非 2026 年新拆机。** Edgesource 2024 年 3 月发布的 *Security Risks of the AeroScope Upgrade Module* 展示了定制 USB Hub 扩展板，以及从模块移出的内部处理器（Figure 3：Hub 正反面；Figure 4：处理器）。[King-Of-Knights 于 2026 年转贴的图片](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5944688781) 源于这份更早的公开研究，**不能据此断言该评论者亲自完成拆机或取得私钥**。

来源：[Edgesource 2024 年原文 §1.5，第 9–10 页及 Figure 3/4](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)。

**必须区分两种不同的 session key：**

1. **AeroScope ↔ dongle 通信会话密钥：** 主机和 dongle 经多步认证/密钥交换建立，用来保护两者之间的传输；见白皮书 §1.6、Figure 5。
2. **飞行器 DroneID 会话密钥：** 飞行器将其加密封装在 CRYP 中；AeroScope 转发 CRYP 给 dongle，后者返回解封后的飞机会话密钥；主机按 key hash 关联该 key，再解密后续 INFP；见 §1.6、Figure 6。

来源：[Edgesource 2024 白皮书第 10–12 页](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)。

论文公开描述了受硬件保护的处理器、加密狗认证及解封流程，但**没有公布 SM2 private scalar、可复现私钥提取结果，也没有充分证实该器件采用 TEE**。论文提到计划面向获准对象提供更详细的 *Technical Addendum*；在取得可核对的公开副本前不能将其当作已公开资料。[原文摘要及脚注](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)。

## 2b. 2026 年 10 月：加密狗调用、密钥声明与验证语料

| 进展/原话范围 | 证据等级 | 精确来源 |
|---|---|---|
| King-Of-Knights 公布控制台输出，**声称成功调用真实 AeroScope dongle**：输入 CRYP/AA（或 A3）后得到 16-byte 飞机 session key，并据此把同会话 INFP/87（或 80）解成连续遥测。未公开 `dji_dongle_decrypt.py` 源码和 dongle 的命令/USB 协议。 | **公开运行演示（日志），尚不可独立复现** | [Issue #1 演示](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456) |
| TheOldCode 表示可以提供 “O4 decryption key”，**但未说明究竟是 SM2 private scalar、dongle 能力还是其他机制**；所引评论没有密钥或独立校验证据。 | **第三方声明，未验证** | [proto17/dji_droneid #63](https://github.com/proto17/dji_droneid/issues/63#issuecomment-6057095721) |
| King-Of-Knights 表示一周内接触到至少三方销售离线解密算法；属于**报价/供给线索**，不是三次已验证的私钥提取。 | **第三方声明，未验证** | [Issue #1 回复](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6062489107) |
| EdwardBlair 提出可以提供**测试语料**，以较高可信度区分① dongle 解密、② 真正持有私钥、③ 其他机制。该评论仅提出验证方案，**没有证明任何提供方已经通过测试**。 | **公开验证方案，尚无测试结果** | [Issue #1 回复](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6062814886) |

**当前边界：** 已有公开协议/参考解密器、第三方 dongle 调用日志及密钥持有声明；但以上资料**仍不能证明 SM2 私钥已被公开、独立验证提取，也不能证明脱离 dongle 的完整软件解码已可复现**。

## 3. 已纠正：Remote ID 的 CMAC KDF 不是 OcuSync DroneID

Issue #1 曾出现以下 KDF：

```text
K_mid  = CMAC(root_key, 01 || "DJI DRONES" || 00 || "SASE" || 80)
RIDkey = CMAC(K_mid,    01 || "DEC KEY"   || 00 || "DJI RID" || 80)
```

当前仓库不再把它写进 O4 DroneID 主密码链。

| 事实 | 状态 | 证据 |
|---|---|---|
| 上述 CMAC 结构最初被公开为 DJI RID/Remote ID 相关 KDF。 | **公开声明** | [原始 KDF 评论](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5772131999) |
| EdwardBlair 后续明确纠正：该 KDF 属于 Remote ID，与 DroneID 不同。 | **已纠正** | [纠正说明](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5929240147) |
| 其进一步说明 RID key 用于保护遥控器 GPS/遥测在“遥控器 -> 飞控”的 DJI 内部传输，飞控之后再发出未加密 Wi-Fi/Bluetooth Remote ID。 | **公开确认（讨论）** | [解释](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5929968912)、[最终澄清](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656) |
| OcuSync DroneID **不使用**上述 RID CMAC 机制。 | **公开确认** | [最终澄清](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656) |

因此当前正确模型是：**随机 AES session key + SM2 公钥封装**，而不是 `root_key -> CMAC -> RIDkey -> INFP`。

## 4. O4/O4+ 跨机型范围

| 事实 | 状态 | 证据 |
|---|---|---|
| 本仓库完整本地实测链来自 DJI Mini 5 Pro。 | **本地已验证** | [README](README.zh-CN.md) |
| EdwardBlair 公开表示，从 Air 3 开始的所有 O4/O4+ 机型（包括行业机）使用相同 DroneID 机制。 | **公开确认（需注明来源）** | [Issue #1 评论](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5716672326) |
| 由于“全 O4/O4+ 一致”来自第三方公开确认而非本仓库逐机型采样，所以继续收集跨机型数据仍有价值。 | **研究边界** | [交叉验证 Issue](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1) |

## 5. PHY/FEC

### 经典 O2 —— 本仓库已复现

```text
sample rate       15.36 MS/s
FFT               1024
subcarrier space  15 kHz
active carriers   600（DC excluded）
symbols           9
normal CP         72
long CP           80
ZC                 root 600 / root 147
data symbols      6 个 QPSK symbol
soft bits         7200
LTE Turbo         K=1408, D=1412
transport         176 bytes
validation        CRC24A + DJI CRC16
```

证据：[O2 解码器](src/o2_droneid_decode.py)、[Turbo 适配器](tools/remove_turbo_soft.c)。

### O4

| 事实 | 状态 | 证据 |
|---|---|---|
| 本项目至少部分 O4 加密 DroneID 抓包可以经过经典 O2-like 9-symbol PHY/FEC shell，并最终同时通过 CRC24A 与 DJI CRC16。 | **本地已验证** | [RUB DroneSecurity 交叉验证回复](https://github.com/RUB-SysSec/DroneSecurity/issues/50#issuecomment-5636324901) |
| EdwardBlair 表示当前 O4 DroneID 解码只需要 ZC root 600；root 147 虽持续存在，但不是解码必需。 | **公开确认（注明来源）** | [Issue #1 评论](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5716726564) |
| root 147 在当前 O4 DroneID 中的实际用途仍未知；“可能与 C2 有关”只是建议，不是已验证结论。 | **未解决** | [同一评论](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5716726564) |
| Air 3S 用户曾公开报告约 500 µs、4 个 ZC 的重复 O4 burst；它究竟属于 DroneID、C2 还是其他状态帧仍未确认。 | **局部观察** | [RUB DroneSecurity Issue #50](https://github.com/RUB-SysSec/DroneSecurity/issues/50) |

在没有更多跨机型/固件双 CRC 样本前，不应把某一种 O4 PHY shell 写成全系列唯一结构。

## 6. 发包触发条件

### Mini 5 Pro —— 本仓库本地观察

- GNSS 定位有效后观察到 CRYP/AA。
- 启动/起飞后观察到 INFP/87 动态遥测。
- 同会话 CRYP 与 INFP 共享 session/hash 标识。

这些是**具体机型/固件观察**，不等于全系列统一规则。

### DragonSDR / WarDragon 当前公开文档

DragonSDR/WarDragon 文档当前写明：O4 DroneID 在电机转动时广播，而仅开机时主要是 OcuSync 控制链路。应将其视为产品文档描述，并继续按机型交叉验证。  
来源：[DragonSDR README](https://github.com/alphafox02/dragonsdr_dji_droneid)、[WarDragon DragonSDR 文档](https://github.com/alphafox02/WarDragon/blob/main/docs/hardware/dragonsdr.md)。

## 7. 开源/商业接收方案现状

| 系统 | 当前公开能力 | 证据 |
|---|---|---|
| DragonSDR 开源接收器 | O2/O3 完整遥测；O4 默认仅 hash ID、频率、RSSI。 | [DragonSDR README](https://github.com/alphafox02/dragonsdr_dji_droneid) |
| DragonScope | 为 O4 增加 SN、飞行器/飞手/Home GPS、高度、速度；当前公开部署要求 license/config 和互联网连接。 | [DragonSDR README](https://github.com/alphafox02/dragonsdr_dji_droneid)、[WarDragon 架构](https://github.com/alphafox02/WarDragon/blob/main/docs/architecture/overview.md) |
| alphafox02 私有实现 | 公开声明端到端完整 O4 解码已经同时解决 online/offline，但未发布其私有实现。 | [online/offline resolved](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704941726)、[确认是完整遥测](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5705619316) |
| 旧 AntSDR 仓库 | 维护者已说明将迁移主线到 `dragonsdr_dji_droneid`。 | [迁移说明](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5883226434) |

必须区分：**私有离线解码器存在** ≠ **公开可复现的私钥恢复方法存在**。


### 历史实现线索：“最多约 100 candidates”

EdwardBlair 还曾在旧 AntSDR 讨论中表示：在判断 alphafox02 并没有相应 key 后，他知道对方采用的实现思路，并称自己已经把“那个特定问题”优化为 constant-time + binary search，候选数量最多约 100，从而避免首包需要数秒处理。**候选对象和具体算法没有公开**。因此这条评论不能被解释为“SM2 私钥只有约 100 个候选”“AES session key 只有约 100 个候选”或“SM2 被破解”。

状态：**PUBLIC-CLAIM / 机制未公开**。  
来源：[AntSDR Issue #27 评论](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5716952989)。

## 8. O2/O3 边界

- 本仓库已经复现经典 O2 明文 DroneID PHY/FEC。
- 不应因为较老 O2/O3 产品是明文，就推断所有 O3 都相同。
- 仓库所有者已经观察到 Inspire 3 / O3 的加密 DroneID，但目前仓库尚未公开一份脱敏抓包供第三方独立复核。因此当前应标记为 **OBSERVED-NOT-YET-PUBLISHED**，不能扩展为“O3 全部加密”或“O3 与 O4 完全相同”。
- DragonSDR 当前公开支持矩阵把其支持的 O2/O3 示例列为可完整解码、O4 默认列为加密检测；这属于产品支持矩阵，不是“所有 O3 协议均明文”的证明。[DragonSDR README](https://github.com/alphafox02/dragonsdr_dji_droneid)

## 9. 当前包解析模型

结合本地样本和公开参考代码：

```text
CRYP:
  key/session identifier
  C1
  C3
  C2
  IV
  encrypted auxiliary field(s)

INFP:
  subtype/selector
  same key/session identifier
  IV/nonce
  encrypted telemetry
```

输入可能是 direct core packet、外层逻辑 envelope 或 V1 service frame，因此偏移不能脱离 envelope 类型单独解释。公开参考 parser 已包含多层 unwrap 和布局校验：[Issue #1 参考实现](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887)。

## 10. 已解决 / 未解决

### 已经足够公开、可实现

- 经典 O2 PHY/FEC/CRC 链。
- O4 CRYP/INFP 的协议角色。
- SM2 封装模型。
- SM3 KDF 与 C3 校验方法。
- 已知 session key 时的 AES-128-CTR INFP 解密。
- 提供正确 SM2 private scalar 后可工作的完整参考 decoder。
- DragonSDR 的公开 O4 检测链。

### 公开层面仍未解决

- AeroScope SM2 private scalar 的公开提取。
- 可公开复现的 dongle key dump / oracle 工作流。
- 所有 O4/O4+ PHY 变体的逐机型端到端确认。
- O4 中 root 147 的准确作用。
- Inspire 3 / O3 加密 DroneID 的公开脱敏样本与第三方复核。
- 不依赖专有密钥材料的公开 DragonScope-equivalent 离线实现。

## 11. 主要来源

核心技术讨论：

- [本项目交叉验证 Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1)
- [AntSDR Issue #27 —— O4 decryption key](https://github.com/alphafox02/antsdr_dji_droneid/issues/27)
- [RUB-SysSec DroneSecurity Issue #50 —— Air 3S O4 PHY](https://github.com/RUB-SysSec/DroneSecurity/issues/50)
- [proto17/dji_droneid Issue #50 —— OcuSync 4](https://github.com/proto17/dji_droneid/issues/50)

当前接收生态：

- [DragonSDR DJI DroneID Receiver](https://github.com/alphafox02/dragonsdr_dji_droneid)
- [WarDragon](https://github.com/alphafox02/WarDragon)
- [WarDragon DragonSDR 文档](https://github.com/alphafox02/WarDragon/blob/main/docs/hardware/dragonsdr.md)

AeroScope dongle：

- [Aerial Defence：Security Risks of the AeroScope Upgrade Module](https://www.aerial-defence.com/security-risks-of-the-aeroscope-upgrade-module-whitepaper/)
- [Edgesource 2024 原始白皮书 PDF（图 3–6）](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)
- [Issue #1 dongle 调用演示](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456)
- [Issue #1 三类解密机制测试语料提议](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6062814886)
- [proto17 #63 O4 密钥提供声明（未验证）](https://github.com/proto17/dji_droneid/issues/63#issuecomment-6057095721)

本仓库可复现代码：

- [O4 packet tool](src/o4_packet_tool.py)
- [O4 tests](tests/test_o4_packet_tool.py)
- [O2 decoder](src/o2_droneid_decode.py)
- [HackRF scanner](src/droneid_hackrf_scanner.py)
- [TurboFEC adapter](tools/remove_turbo_soft.c)

## 12. 后续更新引用规则

以后新增结论时：

1. 原始 IQ + 可复现 CRC/明文结果优先级最高。
2. 第三方结论必须链接到具体评论、commit、论文或文档。
3. “第三方声称全系列一致”必须保留归因，不自动写成本仓库逐机型验证。
4. Remote ID 与 OcuSync DroneID 必须严格分开。
5. 商业/私有实现若无公开代码和测试向量，只写“公开声明存在”。
6. 如果旧解释被纠正，保留“已纠正”条目及来源，防止以后重新混入主链。
