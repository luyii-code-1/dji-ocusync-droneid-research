# DJI OcuSync DroneID Research

[English](README.md) | [简体中文](README.zh-CN.md)

Reproducible DJI OcuSync O2/O4 DroneID research and tools based on raw HackRF IQ captures.

This repository consolidates findings verified as of **2026-08-27** through raw captures, CRC validation, and continuous telemetry. It covers the receive chain, physical layer, packet structure, and cryptographic envelope, with explicit confidence levels and open research steps.

## Contents

- [Status](#status)
- [Tested aircraft and transmission triggers](#tested-aircraft-and-transmission-triggers)
- [Quick start](#quick-start-inspect-aa-or-decrypt-87)
- [Complete research record](#complete-research-record)
- [O4 cryptographic chain](#o4-cryptographic-chain)
- [Reproducible measurements](#reproducible-measurements-and-calculated-values)
- [License](#license)

## Status

| Stage | Status | Evidence |
|---|---|---|
| HackRF signed-int8 IQ input | Verified | Live capture and replay |
| O2 9-symbol OFDM / ZC600+147 | Verified | Correlation peaks and frame structure |
| O2 LTE Turbo transport | Verified | CRC24A remainder equals zero |
| O2 inner payload | Verified | DJI CRC16 remainder equals zero |
| O4 AA/87 logical packets | Verified | Double-CRC-valid captures |
| AA C1 curve point and `C1‖C3‖C2` layout | Strong evidence | Curve checks across multiple sessions |
| `note → 87` | Verified | AES-128-CTR produced coherent sequential telemetry |
| `AA → note` | In research | Requires the SM2 private key or an equivalent decryptor |

## Tested aircraft and transmission triggers

The O4 measurements and cryptographic chain in this repository were obtained from a **DJI Mini 5 Pro**. The observed transmission triggers are:

- **AA key-material packets begin after GPS/GNSS positioning is valid.**
- **87 dynamic telemetry packets begin after the operator presses start/takeoff.**
- Aircraft power-on alone does not produce the validated Mini 5 Pro AA/87 sequence described here.
- In the tested O2/O3 behavior, the aircraft broadcasts the plaintext DroneID payload after power-on, including operation without a connected remote controller.

These are measured protocol behaviors for the tested aircraft and firmware, and should be revalidated for other models and releases.

The confirmed hybrid-encryption chain is:

```text
HackRF IQ
  → ZC / OFDM / Turbo
  → CRC24A + DJI CRC16
  → AA + 87

AA:
  SM2-compatible C1‖C3‖C2
  → 16-byte note                  (private-key step)

87:
  AES-128-CTR(key=note, IV=nonce8 || 0x00×8)
  → SN / UUID / drone / pilot / home telemetry
```

## Repository layout

```text
src/o4_packet_tool.py       Inspect AA and decrypt 87 with a known note
src/o2_droneid_decode.py    Experimental classic O2 PHY/FEC decoder
src/droneid_hackrf_scanner.py
                            Live and replay HackRF scanner
tools/remove_turbo_soft.c   TurboFEC adapter
```

## Quick start: inspect AA or decrypt 87

Requirements: Python 3.10+ and the OpenSSL command-line tool.

```bash
python3 src/o4_packet_tool.py '<complete-AA-hex>'
python3 src/o4_packet_tool.py --note '<16-byte-note-hex>' '<complete-87-hex>'
```

The `note` is a 16-byte AES session key. Multiple 87 packets with the same `hashcode` use the same note and carry individual nonces. A session refresh or aircraft restart changes the hashcode and requires the note paired with the new AA.

The current tool validates AA structure and decrypts same-session 87 packets with a supplied note. Recovering the note from AA requires an SM2 private key or an equivalent local decryption module.

## Sample-rate requirement

HackRF files contain interleaved signed-int8 I/Q samples, or 2 bytes per complex sample. For example:

```bash
hackrf_transfer -r capture.iq -f 2429500000 -s 20000000 -l 16 -g 20 -a 0
```

This records at 20 MS/s. The classic detector operates at 15.36 MS/s, so the input must be resampled first:

```text
20.00 MS/s × 96 / 125 = 15.36 MS/s
```

The analyzer sample rate must match the capture. Resampling preserves the ZC time scale, CP length, FFT window, CFO estimate, and downstream CRC recovery.

## O2 decoder

`src/o2_droneid_decode.py` is an experimental reference implementation. It requires NumPy and a helper built from [TurboFEC](https://github.com/ttsou/turbofec):

```bash
git clone https://github.com/ttsou/turbofec third_party/turbofec
clang -O3 -Ithird_party/turbofec/include -Ithird_party/turbofec/src \
  tools/remove_turbo_soft.c \
  third_party/turbofec/src/turbo_dec.c \
  third_party/turbofec/src/turbo_enc.c \
  third_party/turbofec/src/turbo_rate_match.c \
  -lm -o build/remove_turbo_soft
```

SIMD flags and compiler options may need adjustment on other platforms. A valid decode requires both checks:

```text
CRC24A(176-byte transport) == 0
DJI_CRC16(logical payload) == 0
```

## Publication and privacy

Repository examples use synthetic or anonymized identifiers and locations. Credentials, session keys, and large raw captures belong in the researcher's secure local environment. Third-party code and firmware are referenced through their original sources and licenses. Before publishing captures, sanitize payloads, absolute paths, timestamps, locations, and acquisition metadata that may identify people or devices.

## Responsible use

This project supports interoperability research, spectrum analysis, receiver development, and authorized security research. Its intended scope is passive reception and explicitly authorized testing performed in compliance with applicable radio, privacy, aviation, and computer-security laws.

DJI, OcuSync, and related product names belong to their respective owners. This project is independent and is not affiliated with or endorsed by DJI.

## Complete research record

### Evidence standard

The project uses this evidence order:

```text
raw IQ > independently reproduced double-CRC result > primary technical material
       > public code > discussion comments > hypothesis
```

Signal detection and payload decoding are separate claims:

- ZC, CP, or spectral peaks establish a physical-layer candidate;
- a valid CRC24A establishes recovery of the 176-byte transport block;
- a valid DJI CRC16 establishes consistent logical-packet boundaries and content;
- a double-CRC-valid encrypted payload is still ciphertext until its cryptographic layer is verified.

### HackRF data convention

HackRF raw files use interleaved signed-int8 I/Q:

```text
I0 Q0 I1 Q1 ...
2 bytes / complex sample
duration = file_bytes / 2 / sample_rate
```

The center DC spike should be removed, notched, or guarded during detection and spectrum statistics. Reference implementations may use the opposite I+jQ/I−jQ convention; choose the convention by ZC correlation rather than assumption.

#### 20 MS/s and 15.36 MS/s

File size, bytes per complex sample, and reported duration provide an independent sample-rate check. A 20 MS/s capture enters the classic 15.36 MS/s detector at:

```text
15.36 / 20 = 96 / 125
```

Large files should use stateful blockwise polyphase resampling with overlap. Loading a gigabyte-scale IQ file at once is unnecessary.

### O2 physical-layer gold standard

The verified classic O2 DroneID structure is:

```text
sample rate       15.36 MS/s
FFT               1024
subcarrier space  15 kHz
active carriers   600 (DC excluded)
symbols           9
normal CP         72
long CP           80
symbol index 3    ZC root 600
symbol index 5    ZC root 147
data symbols      1,2,4,6,7,8
```

A 601-point Zadoff–Chu sequence is generated, its center element is removed, and the remaining 600 values are mapped around DC. A frame spans about 9,880 samples, or 643.2 µs.

### O2 FEC chain

```text
6 QPSK symbols × 600 carriers × 2 bits = 7200 soft bits
→ Gold descramble
→ LTE reverse rate matching, E=7200, RV=0
→ LTE Turbo, K=1408, D=1412
→ 176-byte transport
→ CRC24A
→ variable logical payload
→ DJI CRC16
```

The chain has been independently reproduced from raw IQ through simultaneous zero CRC24A and DJI CRC16 remainders. Public samples use anonymized identity and location data.

### Scanning and frequency observations

One 2.4 GHz experiment used the following 15 MHz raster:

```text
2399.5 / 2414.5 / 2429.5 / 2444.5 / 2459.5 MHz
```

These are experimental scan centers rather than universal official frequencies. Behavior can vary by model, region, and firmware. A single HackRF cannot observe the full band simultaneously, so dwell duration and revisit rate trade directly against each other.

A 15.36 MS/s capture centered at 2407.5 MHz spans approximately 2399.82–2415.18 MHz. A complete classification requires the full burst bandwidth to fit inside the receive window; edge coverage is suitable for energy and partial-spectrum candidates.

### Separating the OcuSync main link from DroneID

Both observed O2 and O4 main links use LTE-like numerology: 15 kHz spacing, FFT1024, about 72 samples of CP, roughly 600 active carriers, and a 5 ms / 200 Hz timing structure. Therefore, 5 ms periodicity alone does not identify DroneID.

Main video, control/C2, Wi-Fi/Bluetooth RID, and DJI DroneID require separate classification. High-duty-cycle main links are best handled with joint CP/ZC, bandwidth, and frame-structure analysis; a simple median-plus-MAD power threshold changes behavior with occupancy and baseline power.

### O4 packet findings

Observed O4 logical types include `AA`, `A7`, and `87`. AA and 87 associate through a four-byte hashcode. Third-party material describes A7 as an unencrypted information packet; the confirmed 87 decryption chain does not depend on A7.

Flight-state captures produced AA and same-hash 87 packets. Once a service returned the 16-byte note for AA, subsequent 87 packets decrypted locally. See the cryptographic-chain section below.

Two 20 MS/s captures at different 2.4 GHz centers each produced a double-CRC-valid 87 after correct resampling. Sample-rate consistency is therefore a mandatory preflight check for ZC, CP, and CRC processing.

### O4 PHY boundary

Some captured O4 encrypted packets retain the classic 9-symbol root600/root147 shell and pass through the established O2 PHY/FEC chain into double-CRC-valid logical packets. Public discussion also reports a newer 10-symbol dynamic-root structure:

```text
Q Q Q | ZA ZA | ZB ZB | Q Q Q
```

Its six QPSK data symbols again produce 7,200 bits. This structure remains an end-to-end validation hypothesis; O4 models and protocol versions should be classified independently.

### AA/87 transmission conditions

The O4 captures in this study are from a DJI Mini 5 Pro. AA key-material transmission begins only after GPS/GNSS positioning is valid. The validated 87 dynamic stream begins after the operator presses start/takeoff. O2/O3 aircraft exhibit a different behavior: their plaintext DroneID payload is transmitted after aircraft power-on, including operation without a connected remote-controller link.

### Cryptanalytic boundary

- Standard SM2 retains roughly 128-bit generic security under a small set of known AA→note pairs.
- The complete AES-128 note keyspace contains `2^128` candidates.
- Fixed 87 plaintext fields provide an efficient verifier for a constrained key hypothesis.
- An aircraft-side SM2 public key identifies the hierarchy, key ID, and encryption call path; AA decryption uses the corresponding private key.

Promising implementation research includes low-entropy note derivation, C1 or nonce reuse, firmware key IDs and public keys, and legally obtained offline receiver implementations.

### Reproduction checklist

1. Cross-check the sample rate using the capture command, file size, and reported duration.
2. Record the actual center frequency and gain settings from the capture command.
3. Identify DroneID using CP, ZC, symbol count, and both CRCs together.
4. Record a ZC peak as a PHY candidate and a double-CRC result as a payload decode.
5. Label CRC-valid ciphertext as encrypted transport and preserve the original payload.
6. Attribute third-party terminology to its source and verify protocol claims independently.
7. Publish anonymized identifiers, locations, and credential fields.

### Recommended experiment artifacts

For every candidate frame, preserve at least:

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

`decode.json` should record the sample rate, center frequency, frame start, CP/ZC scores, CFO, CRC results, logical length, and payload SHA-256. Sanitize absolute paths, timestamps, locations, and identity fields before publication.

### Next research steps

- verify the standard SM2 KDF and C3 with additional independent sessions;
- locate the business public key and key ID in aircraft firmware;
- study legally obtained receivers with offline O4 parsing capability;
- implement stateful streaming resampling from 20 to 15.36 MS/s;
- add the 10-symbol dynamic-root O4+ detector as an independent pipeline;
- expand synthetic packet and unit-test coverage.

## O4 cryptographic chain

### 1. Confirmed session relationship

AA carries key material and 87 carries dynamic telemetry. Bytes `6:10` of each logical packet contain a four-byte `hashcode`. An AA and its same-session 87 packets share this value.

```text
AA(hash=H) → note K
87(hash=H, nonce=N1) → AES-CTR(K, N1)
87(hash=H, nonce=N2) → AES-CTR(K, N2)
...
```

One observed note successfully decrypted at least eight 87 packets with the same hash. Sequence numbers, times, coordinates, and altitude changed coherently. The note is a session key, while each 87 packet carries its own nonce. A refreshed session requires the note paired with the new hash.

### 2. Common logical-packet header

```text
offset  size  meaning
0       1     packet_length_minus_3
1       1     message type / subtype
2       4     ASCII marker: CRYP or INFP
6       4     hashcode
...     ...   type-specific body
last-2  2     DJI CRC16, little-endian
```

The logical length is `packet[0] + 3`. DJI CRC16 uses initial value `0x3692` and reflected polynomial `0x8408`; a complete valid logical packet has a zero remainder.

### 3. AA layout

Observed AA packets begin with:

```text
AA 13 43 52 59 50 [hashcode]
```

`43 52 59 50` is ASCII `CRYP`.

```text
offset    size  interpretation
10:74     64    C1 = X || Y, two 32-byte big-endian coordinates
74:106    32    C3 candidate
106:122   16    C2 candidate; plaintext length matches note
122:...   ...   remaining protocol fields and tail data
```

C1 values from four independent sessions satisfy the Chinese SM2 curve equation:

```text
p = FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
a = FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
b = 28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93

y² ≡ x³ + ax + b (mod p)
```

The 64 + 32 + 16 lengths match raw-point SM2 `C1‖C3‖C2` exactly. Standard SM2 public-key encryption is therefore a high-confidence conclusion. Final confirmation requires computing the shared point with a private key and verifying both the KDF output and C3. A custom ECIES construction using the SM2 curve and the same envelope remains a small residual possibility.

Under the standard SM2 hypothesis:

```text
S    = d × C1
mask = SM2_KDF(S.x || S.y, 16)
note = C2 XOR mask
C3 ?= SM3(S.x || note || S.y)
```

The aircraft uses a public key to create AA; the decryptor requires the corresponding private key. The open implementation currently accepts the private-key step as an external dependency.

### 4. 87 layout and verified decryption

```text
offset   size       meaning
0        1          0x87
1        1          0x10
2:6      4          ASCII "INFP"
6:10     4          hashcode
10:18    8          per-packet nonce
18:20    2          ciphertext length, uint16 little-endian
20:...   variable   ciphertext
last-2   2          DJI CRC16
```

Verified decryption parameters:

```text
cipher = AES-128-CTR
key    = note                         # 16 bytes
IV     = packet[10:18] || 00×8        # 16 bytes
body   = packet[20 : 20 + uint16_le(packet[18:20])]
```

CTR mode provides confidentiality rather than authentication. Validate fixed fields, bounds, sequence progression, and telemetry continuity after decryption. The outer DJI CRC16 proves logical-packet transport integrity, independently of the note.

### 5. Observed plaintext fields

The verified plaintext includes version, sequence, state, a 16-byte serial-number field, raw coordinates, altitude, relative height, three axis values, yaw, millisecond time, pilot coordinates, home coordinates, product type, and a variable-length UUID.

The validated 109-byte plaintext uses the following offsets. Multi-byte numeric fields are little-endian:

| Plaintext offset | Size | Type | Observed meaning / conversion |
|---:|---:|---|---|
| 0 | 1 | uint8 | message marker, observed `0x10` |
| 1 | 1 | uint8 | protocol version |
| 2 | 2 | uint16 | sequence number |
| 4 | 2 | uint16 | state flags |
| 6 | 16 | ASCII | serial-number field, NUL padded |
| 22 | 4 | int32 | aircraft longitude, radians × 10⁷ |
| 26 | 4 | int32 | aircraft latitude, radians × 10⁷ |
| 30 | 2 | int16 | altitude |
| 32 | 2 | int16 | relative height × 10 |
| 34 | 2 | int16 | X / velocity-like raw value |
| 36 | 2 | int16 | Y / velocity-like raw value |
| 38 | 2 | int16 | Z / velocity-like raw value |
| 40 | 2 | int16 | yaw × 100 degrees |
| 42 | 8 | uint64 | Unix time in milliseconds |
| 50 | 4 | int32 | pilot latitude, radians × 10⁷ |
| 54 | 4 | int32 | pilot longitude, radians × 10⁷ |
| 58 | 4 | int32 | home longitude, radians × 10⁷ |
| 62 | 4 | int32 | home latitude, radians × 10⁷ |
| 66 | 1 | uint8 | product type |
| 67 | 1 | uint8 | UUID length |
| 68 | variable | ASCII | UUID |

Coordinates use signed 32-bit fixed-point radians:

```text
degrees = raw_i32 / 10_000_000 × 180 / π
```

Field layouts may vary by model and protocol version. Parsers should retain the raw plaintext and apply strict bounds checks.

### 6. A3 / 80 status

Third-party service material describes A3/80 as another key-material/dynamic-packet pair. Complete cryptographic verification in this repository currently covers AA→note→87. A3/80 offsets, IV construction, and field layouts remain separate sample-validation tasks.

### 7. Cryptanalytic boundary

Standard AES-128 exhaustive search and generic attacks against SM2-256 both provide roughly 128-bit security. Productive implementation checks include:

- low-entropy note derivation or time-based seeds;
- repeated AA C1 points;
- nonce collisions under the same note;
- business public keys, key IDs, or offline decryptors in firmware;
- curve-point validation and side-channel behavior in explicitly authorized implementations.

The public key may be present in aircraft firmware, configuration storage, or a secure module. It can confirm the key hierarchy and locate the encryption path; AA decryption requires the matching private key. Private-key deployment is more likely in a server HSM or an offline-capable receiver.

## Reproducible measurements and calculated values

This document records the numerical observations behind the protocol conclusions. Values are grouped by capture and processing stage so they can be reproduced independently. Device identifiers, exact locations, complete encrypted packets, and active session keys are anonymized.

### 1. IQ representation and duration calculation

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

### 2. Measured I/Q characteristics

#### O4 / Mini 5 Pro captures

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

#### O2 / Mini 2 captures

| State | Duration | Mean I | Mean Q | Approx. I-channel std. dev. |
|---|---:|---:|---:|---:|
| motor off | 6.3402667 s | -1.15047 | -4.31490 | 5.92 |
| motor on | 6.4853333 s | -1.15364 | -4.33045 | 9.064 |
| motor action | 6.5194667 s | -1.15234 | -4.30780 | 8.993 |

No material clipping was observed. The DC means remain nearly constant while activity changes the variance, which supports subtracting the complex mean independently for each analysis window.

### 3. RF bandwidth and centroid measurements

#### O4 main-link observations

| State | Approximate occupied range | 99% bandwidth | Centroid |
|---|---|---:|---:|
| motor on, pending | 2403.071–2411.992 MHz | 8.921 MHz | 2408.230 MHz |
| motor on, action | 2403.057–2411.982 MHz | 8.926 MHz | 2408.007 MHz |

The nominal channel is approximately 10 MHz wide. A separate narrow feature around 2402.05 MHz measured about 1.0–1.1 MHz and was excluded from the main OFDM measurements.

#### O2 main-link observations

The measured occupied range was approximately 2403.0–2412.0 MHz with a 99% bandwidth near 8.98 MHz. Motor-on and action average PSDs had correlation near 0.9918.

### 4. Timing measurements

#### O4 envelope

| State | Strong envelope component | Period |
|---|---:|---:|
| motor off | 400.048 Hz | 2.4997 ms |
| motor on, pending | 200.043 Hz | 4.9989 ms |
| motor on, action | 200.024 Hz | 4.9994 ms |

The pending/action 5 ms templates had correlation near 0.991. An approximate frame divided into 0–3.27 ms strong activity, a 3.27–4.47 ms gap, and 4.47–5.00 ms strong activity. Activity above a 10 dB threshold was approximately 18.0% off, 71.3% pending, and 66.5% action.

#### O2 envelope

| State | Strong envelope component | Activity above 10 dB |
|---|---:|---:|
| motor off | 499.98 Hz | 25.55% |
| motor on | 199.99 Hz | 77.16% |
| motor action | 200.016 Hz | 77.25% |

The shared 200 Hz / 5 ms feature shows that periodicity alone identifies an OcuSync timing family, not a specific DroneID frame.

### 5. OFDM numerology calculations

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

#### O4 main-link evidence after 20→15.36 MS/s resampling

- FFT candidate scan from 960 through 1088 selected N=1024 clearly;
- N=1024 CP-correlation 99.5th percentile: approximately 0.923;
- strongest CP correlation: approximately 0.992;
- common CP-peak separation: approximately 1095 samples;
- active carriers: approximately 600–620;
- measured reciprocal timing and occupied bandwidth agree with 15 kHz spacing.

#### O2 main-link evidence

- N=1024 CP-correlation 99.9th percentile: off 0.9574, on 0.9813, action 0.9779;
- strongest correlations reached approximately 0.994–0.997;
- common CP separation: 1094–1101 samples, with 1095–1097 dominant;
- normal CP: approximately 72 samples, occasional long CP near 80;
- active span: approximately 605 bins or 9.075 MHz.

### 6. Classic O2 DroneID gold-frame measurements

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

### 7. The two CRC calculations

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

### 8. Sample-rate correction outcome on O4 captures

The two 20 MS/s recordings produced maximum classic-ZC scores near 0.166 and 0.177 when interpreted directly at 15.36 MS/s. After 96/125 resampling:

| Center | Paired-ZC candidates | Double-CRC-valid logical packets | Packet type | Event time in capture |
|---:|---:|---:|---:|---:|
| 2429.5 MHz | 3 | 1 | `0x87` | approximately 15.7836 s |
| 2444.5 MHz | 4 | 1 | `0x87` | approximately 21.0137 s |

This establishes that the files contained DroneID-family frames and that the original low correlation was a time-scale mismatch rather than absence of RF activity.

### 9. AA / 87 structural measurements

#### AA

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

#### 87

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

### 10. Confidence classification

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

## License

Original content in this repository is licensed under the [GNU General Public License v3.0](LICENSE). Third-party dependencies remain subject to their respective licenses.
