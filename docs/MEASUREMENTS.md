# Reproducible Measurements and Calculated Values

[English](MEASUREMENTS.md) | [简体中文](MEASUREMENTS.zh-CN.md)

This document records the numerical observations behind the protocol conclusions. Values are grouped by capture and processing stage so they can be reproduced independently. Device identifiers, exact locations, complete encrypted packets, and active session keys are anonymized.

## 1. IQ representation and duration calculation

HackRF produces interleaved signed 8-bit samples:

```text
byte 0 = I0
byte 1 = Q0
byte 2 = I1
byte 3 = Q1
...
```

Each complex sample occupies two bytes:

```text
complex_samples = file_size_bytes / 2
duration_seconds = file_size_bytes / (2 × sample_rate_hz)
```

Two O4 recordings made with `hackrf_transfer -s 20000000` demonstrate why the capture command and file size must be checked together:

| Capture center | File size | Duration at actual 20 MS/s | Apparent duration at 15.36 MS/s |
|---:|---:|---:|---:|
| 2429.5 MHz | 740,294,656 B | 18.507366400 s | 24.098133333 s |
| 2444.5 MHz | 974,127,104 B | 24.353177600 s | 31.709866667 s |

The exact ratio between the two apparent durations is the resampling ratio:

```text
20.00 / 15.36 = 125 / 96
15.36 / 20.00 = 96 / 125 = 0.768
```

The correct processing path is:

```text
HackRF 20 MS/s signed-int8 IQ
  → DC removal
  → polyphase resampling, up=96, down=125
  → 15.36 MS/s complex IQ
  → classic ZC / OFDM detector
```

## 2. Measured I/Q characteristics

### O4 / Mini 5 Pro captures

| State | Duration | Mean I | Mean Q | Approx. sample std. dev. |
|---|---:|---:|---:|---:|
| motor off | 10.8462 s | -1.208 | -4.311 | 1.84 |
| motor on, pending | 10.3678 s | -1.195 | -4.308 | 10.86 |
| motor on, action | 8.0740 s | -1.184 | -4.302 | 8.64 |

Additional checks:

- I/Q gain mismatch: below 0.01 dB;
- I/Q correlation: approximately zero;
- no material signed-int8 clipping was observed;
- the stable nonzero mean is consistent with the HackRF center/DC offset and should be removed before correlation.

### O2 / Mini 2 captures

| State | Duration | Mean I | Mean Q | Approx. I-channel std. dev. |
|---|---:|---:|---:|---:|
| motor off | 6.3402667 s | -1.15047 | -4.31490 | 5.92 |
| motor on | 6.4853333 s | -1.15364 | -4.33045 | 9.064 |
| motor action | 6.5194667 s | -1.15234 | -4.30780 | 8.993 |

No material clipping was observed. The DC means remain nearly constant while activity changes the variance, which supports subtracting the complex mean independently for each analysis window.

## 3. RF bandwidth and centroid measurements

### O4 main-link observations

| State | Approximate occupied range | 99% bandwidth | Centroid |
|---|---|---:|---:|
| motor on, pending | 2403.071–2411.992 MHz | 8.921 MHz | 2408.230 MHz |
| motor on, action | 2403.057–2411.982 MHz | 8.926 MHz | 2408.007 MHz |

The nominal channel is approximately 10 MHz wide. A separate narrow feature around 2402.05 MHz measured about 1.0–1.1 MHz and was excluded from the main OFDM measurements.

### O2 main-link observations

The measured occupied range was approximately 2403.0–2412.0 MHz with a 99% bandwidth near 8.98 MHz. Motor-on and action average PSDs had correlation near 0.9918.

## 4. Timing measurements

### O4 envelope

| State | Strong envelope component | Period |
|---|---:|---:|
| motor off | 400.048 Hz | 2.4997 ms |
| motor on, pending | 200.043 Hz | 4.9989 ms |
| motor on, action | 200.024 Hz | 4.9994 ms |

The pending/action 5 ms templates had correlation near 0.991. An approximate frame divided into 0–3.27 ms strong activity, a 3.27–4.47 ms gap, and 4.47–5.00 ms strong activity. Activity above a 10 dB threshold was approximately 18.0% off, 71.3% pending, and 66.5% action.

### O2 envelope

| State | Strong envelope component | Activity above 10 dB |
|---|---:|---:|
| motor off | 499.98 Hz | 25.55% |
| motor on | 199.99 Hz | 77.16% |
| motor action | 200.016 Hz | 77.25% |

The shared 200 Hz / 5 ms feature shows that periodicity alone identifies an OcuSync timing family, not a specific DroneID frame.

## 5. OFDM numerology calculations

The normalized complex-correlation score used for a reference sequence is:

```text
score(r, s) = |Σ conj(s[n]) r[n]| / sqrt(Σ|r[n]|² × Σ|s[n]|²)
```

CP correlation and CFO use the repeated prefix/useful-symbol samples:

```text
P = Σ conj(x[n]) x[n + NFFT]
cp_score = |P| / sqrt(Σ|x[n]|² × Σ|x[n + NFFT]|²)
cfo_hz = angle(P) × Fs / (2π × NFFT)
```

The implementation combines multiple normal-CP symbols for a more stable CFO estimate.

At 15.36 MS/s:

```text
FFT useful duration = 1024 / 15,360,000
                    = 66.6666667 µs

subcarrier spacing = 15,360,000 / 1024
                   = 15,000 Hz

normal symbol duration ≈ (1024 + 72) / 15,360,000
                       ≈ 71.3542 µs
```

### O4 main-link evidence after 20→15.36 MS/s resampling

- FFT candidate scan from 960 through 1088 selected N=1024 clearly;
- N=1024 CP-correlation 99.5th percentile: approximately 0.923;
- strongest CP correlation: approximately 0.992;
- common CP-peak separation: approximately 1095 samples;
- active carriers: approximately 600–620;
- measured reciprocal timing and occupied bandwidth agree with 15 kHz spacing.

### O2 main-link evidence

- N=1024 CP-correlation 99.9th percentile: off 0.9574, on 0.9813, action 0.9779;
- strongest correlations reached approximately 0.994–0.997;
- common CP separation: 1094–1101 samples, with 1095–1097 dominant;
- normal CP: approximately 72 samples, occasional long CP near 80;
- active span: approximately 605 bins or 9.075 MHz.

## 6. Classic O2 DroneID gold-frame measurements

| Quantity | Measured value |
|---|---:|
| rough burst start | 1.192375 s |
| refined OFDM start | 1.19237793 s |
| total frame samples | 9,880 |
| calculated frame duration | 643.229 µs |
| fine CFO | approximately +1.106 kHz |
| fractional timing correction | approximately -3.715 samples |
| root-600 correlation | approximately 0.928 |
| root-147 correlation | approximately 0.843 |
| typical data-symbol false-ZC score | approximately 0.13–0.14 |
| continuous spectral width | approximately 9.70 MHz |
| 99% bandwidth | approximately 8.94 MHz |
| center offset | approximately +26 kHz |

The nine-symbol sample count follows from the useful symbols and CP sequence:

```text
9 × 1024 + (80 + 7×72 + 80) = 9,880 samples
9,880 / 15,360,000 = 0.0006432291667 s
```

## 7. The two CRC calculations

The reference O2 decode recovered a 176-byte transport block. Its first 173 bytes are protected by CRC24A:

| Check | Received bytes/value | Independently calculated | Full-block remainder |
|---|---|---|---:|
| outer CRC24A | `34 9F E5` / `0x349FE5` | `0x349FE5` | `0x000000` |
| inner DJI CRC16 | `4D E5` little-endian / `0xE54D` | `0xE54D` | `0x0000` |

CRC24A uses polynomial `0x864CFB` with a zero initial remainder. DJI CRC16 uses initial value `0x3692` and reflected polynomial `0x8408`.

```text
outer_ok = CRC24A(transport_176) == 0
inner_ok = DJI_CRC16(logical_payload) == 0
decode_ok = outer_ok and inner_ok
```

The recovered logical payload length was 91 bytes (`payload[0] + 3`). Identity and position fields from the retained sample are omitted from the public measurement record.

## 8. Sample-rate correction outcome on O4 captures

The two 20 MS/s recordings produced maximum classic-ZC scores near 0.166 and 0.177 when interpreted directly at 15.36 MS/s. After 96/125 resampling:

| Center | Paired-ZC candidates | Double-CRC-valid logical packets | Packet type | Event time in capture |
|---:|---:|---:|---:|---:|
| 2429.5 MHz | 3 | 1 | `0x87` | approximately 15.7836 s |
| 2444.5 MHz | 4 | 1 | `0x87` | approximately 21.0137 s |

This establishes that the files contained DroneID-family frames and that the original low correlation was a time-scale mismatch rather than absence of RF activity.

## 9. AA / 87 structural measurements

### AA

```text
declared logical length = 0xAA + 3 = 173 bytes
header                  = AA 13 "CRYP"
hashcode                = 4 bytes at offsets 6:10
C1                      = 64 bytes at offsets 10:74
C3 candidate            = 32 bytes at offsets 74:106
C2 candidate            = 16 bytes at offsets 106:122
SM2 envelope core       = 64 + 32 + 16 = 112 bytes
```

Four C1 values from four independent sessions were tested; all four satisfied the SM2 curve equation. The observed C2 length equals the 16-byte note returned for the same session.

### 87

```text
declared logical length = 0x87 + 3 = 138 bytes
header                  = 87 10 "INFP"
hashcode                = 4 bytes at offsets 6:10
nonce                   = 8 bytes at offsets 10:18
ciphertext length       = uint16 little-endian at offsets 18:20
observed encrypted body = 109 bytes in the validated sample
AES IV                   = nonce8 || 00 00 00 00 00 00 00 00
```

One recovered note decrypted eight unique 87 packets from the same hash session. Their sequence numbers were 141, 262, 271, 314, 348, 395, 404, and 443 over approximately 164 seconds. Reported altitude progressed through an observed range of roughly 78–99 units, while identifiers and reference coordinates remained consistent.

This multi-packet continuity simultaneously verifies the key, CTR IV construction, field offsets, time progression, and session mapping.

## 10. Confidence classification

| Finding | Confidence |
|---|---|
| HackRF byte order and sample duration equations | Verified |
| 20→15.36 MS/s ratio 96/125 | Exact calculation |
| O2 FFT1024 / 15 kHz / CP72–80 / 600 carriers | Verified |
| O2 9-symbol root600/root147 shell | Verified |
| O2 transport and logical payload | Verified by two CRCs |
| O4 AA/87 logical packet extraction | Verified by two CRCs |
| 87 AES-128-CTR key and IV construction | Verified across eight packets |
| AA C1 on the SM2 curve | Verified across four sessions |
| AA uses standard SM2 `C1‖C3‖C2` in every detail | Strong evidence; private-key verification pending |
| A3/80 uses identical offsets and cipher construction | Separate validation task |
