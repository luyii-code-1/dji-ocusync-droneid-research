# O4 AA / 87 密码学链路

[English](O4_CRYPTO_CHAIN.md) | [简体中文](O4_CRYPTO_CHAIN.zh-CN.md)

## 1. 已确认的会话关系

AA 是关键材料包，87 是动态遥测包。逻辑包 bytes `6:10` 是 4 字节 `hashcode`。同一会话的 AA 与 87 共享 hashcode。

```text
AA(hash=H) → note K
87(hash=H, nonce=N1) → AES-CTR(K, N1)
87(hash=H, nonce=N2) → AES-CTR(K, N2)
...
```

实测中，一个 note 成功解密同一 hash 下至少 8 个不同 87，序号、时间、坐标和高度连续合理。它不是每包一个密钥，而是会话密钥。会话刷新后旧 note 不再适用。

## 2. 通用逻辑包头

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

## 3. AA 布局

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

## 4. 87 布局与已验证解密

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

## 5. 已知明文结构（当前样本）

已验证明文包含：版本、sequence、state、16 字节 SN、经纬度原始值、高度、相对高度、三轴量、yaw、毫秒时间、飞手坐标、返航点坐标、产品类型与可变长度 UUID。

经纬度是带符号 32 位弧度定点值：

```text
degrees = raw_i32 / 10_000_000 × 180 / π
```

字段布局可能随型号或协议版本变化，解析器应保留原始明文并对长度做边界检查。

## 6. A3 / 80 的状态

第三方服务资料将 A3/80 描述为与 AA/87 相同的“关键包/动态包”配对。当前完整密码学实测确认集中在 AA→note→87；A3/80 的偏移、IV 和字段仍列为独立样本验证项目。

## 7. 密码分析边界

标准 AES-128 的完整密钥空间和 SM2-256 的通用攻击都具有约 128 位安全强度，直接暴力不可行。更有意义的检查包括：

- note 是否由低熵种子或时间字段派生；
- 不同 AA 是否复用 C1；
- 相同 note 下 87 nonce 是否碰撞；
- 固件是否包含业务公钥、key ID 或离线解密模块；
- 经授权的实现是否遗漏曲线点验证或存在侧信道。

公钥可能存在于飞行器固件、配置区或安全模块中，可用于确认密钥体系和定位实现。AA 解密需要对应私钥；其部署位置更可能是服务器 HSM 或具备离线解析能力的接收设备。
