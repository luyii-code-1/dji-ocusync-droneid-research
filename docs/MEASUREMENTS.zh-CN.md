# 可复现测量值与计算过程

[English](MEASUREMENTS.md) | [简体中文](MEASUREMENTS.zh-CN.md)

本文记录协议结论背后的具体数值，并按采集与处理阶段组织，便于独立复现。设备身份、精确位置、完整加密报文和有效会话密钥均采用脱敏表达。

## 1. IQ 表示与时长计算

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

## 2. I/Q 实测特征

### O4 / Mini 5 Pro

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

### O2 / Mini 2

| 状态 | 时长 | Mean I | Mean Q | 近似 I 通道标准差 |
|---|---:|---:|---:|---:|
| 电机关闭 | 6.3402667 s | -1.15047 | -4.31490 | 5.92 |
| 电机开启 | 6.4853333 s | -1.15364 | -4.33045 | 9.064 |
| 电机动作 | 6.5194667 s | -1.15234 | -4.30780 | 8.993 |

未观察到显著削顶。不同状态下 DC 均值近似稳定，而信号活动主要改变方差，因此每个分析窗口应独立减去 complex mean。

## 3. RF 带宽与质心

### O4 主链路

| 状态 | 近似占用范围 | 99% 带宽 | 质心 |
|---|---|---:|---:|
| 电机开启、等待 | 2403.071–2411.992 MHz | 8.921 MHz | 2408.230 MHz |
| 电机开启、动作 | 2403.057–2411.982 MHz | 8.926 MHz | 2408.007 MHz |

名义信道宽度约为 10 MHz。2402.05 MHz 附近另有约 1.0–1.1 MHz 的窄带特征，主 OFDM 数值统计时已将其排除。

### O2 主链路

占用范围约为 2403.0–2412.0 MHz，99% 带宽约 8.98 MHz。motor-on 与 action 平均 PSD 的相关系数约为 0.9918。

## 4. 时间结构

### O4 包络

| 状态 | 强包络分量 | 周期 |
|---|---:|---:|
| 电机关闭 | 400.048 Hz | 2.4997 ms |
| 电机开启、等待 | 200.043 Hz | 4.9989 ms |
| 电机开启、动作 | 200.024 Hz | 4.9994 ms |

等待/动作状态的 5 ms 模板相关约为 0.991。近似一帧可分为 0–3.27 ms 强活动、3.27–4.47 ms 间隔、4.47–5.00 ms 强活动。高于 10 dB 门限的活动比例约为：关闭 18.0%、等待 71.3%、动作 66.5%。

### O2 包络

| 状态 | 强包络分量 | 高于 10 dB 的活动比例 |
|---|---:|---:|
| 电机关闭 | 499.98 Hz | 25.55% |
| 电机开启 | 199.99 Hz | 77.16% |
| 电机动作 | 200.016 Hz | 77.25% |

O2/O4 共有的 200 Hz / 5 ms 特征首先指向 OcuSync 时间结构家族，具体 DroneID 帧还需要 CP、ZC、符号数和 CRC 联合确认。

## 5. OFDM 参数计算

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

### O4 主链路：20→15.36 MS/s 后

- FFT 候选 960–1088 中 N=1024 明显最优；
- N=1024 CP 相关 99.5 分位约 0.923；
- 最强 CP 相关约 0.992；
- 常见 CP 峰间距约 1095 samples；
- active carriers 约 600–620；
- 倒数时间尺度与占用带宽均符合 15 kHz 子载波间隔。

### O2 主链路

- N=1024 CP 相关 99.9 分位：关闭 0.9574、开启 0.9813、动作 0.9779；
- 最强相关约 0.994–0.997；
- 常见 CP 间距 1094–1101 samples，主值 1095–1097；
- normal CP 约 72 samples，偶发 long CP 约 80；
- active span 约 605 bins，即 9.075 MHz。

## 6. 经典 O2 DroneID 金标准帧

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

## 7. 两个 CRC 计算值

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

## 8. O4 采样率修正结果

两个 20 MS/s 文件直接按 15.36 MS/s 解释时，经典 ZC 最大分数约为 0.166 和 0.177。完成 96/125 重采样后：

| 中心频率 | ZC 配对候选 | 双 CRC 有效逻辑包 | 包类型 | 文件内事件时间 |
|---:|---:|---:|---:|---:|
| 2429.5 MHz | 3 | 1 | `0x87` | 约 15.7836 s |
| 2444.5 MHz | 4 | 1 | `0x87` | 约 21.0137 s |

这证明两份文件包含 DroneID 家族帧，并且初始低相关来自时间尺度不匹配。

## 9. AA / 87 结构数值

### AA

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

### 87

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

## 10. 结论置信度

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
