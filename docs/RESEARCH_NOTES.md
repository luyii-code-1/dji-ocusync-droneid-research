# O2 / O4 DroneID Research Notes

[English](RESEARCH_NOTES.md) | [简体中文](RESEARCH_NOTES.zh-CN.md)

## Evidence standard

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

## HackRF data convention

HackRF raw files use interleaved signed-int8 I/Q:

```text
I0 Q0 I1 Q1 ...
2 bytes / complex sample
duration = file_bytes / 2 / sample_rate
```

The center DC spike should be removed, notched, or guarded during detection and spectrum statistics. Reference implementations may use the opposite I+jQ/I−jQ convention; choose the convention by ZC correlation rather than assumption.

### 20 MS/s and 15.36 MS/s

File size, bytes per complex sample, and reported duration provide an independent sample-rate check. A 20 MS/s capture enters the classic 15.36 MS/s detector at:

```text
15.36 / 20 = 96 / 125
```

Large files should use stateful blockwise polyphase resampling with overlap. Loading a gigabyte-scale IQ file at once is unnecessary.

## O2 physical-layer gold standard

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

## O2 FEC chain

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

## Scanning and frequency observations

One 2.4 GHz experiment used the following 15 MHz raster:

```text
2399.5 / 2414.5 / 2429.5 / 2444.5 / 2459.5 MHz
```

These are experimental scan centers rather than universal official frequencies. Behavior can vary by model, region, and firmware. A single HackRF cannot observe the full band simultaneously, so dwell duration and revisit rate trade directly against each other.

A 15.36 MS/s capture centered at 2407.5 MHz spans approximately 2399.82–2415.18 MHz. A complete classification requires the full burst bandwidth to fit inside the receive window; edge coverage is suitable for energy and partial-spectrum candidates.

## Separating the OcuSync main link from DroneID

Both observed O2 and O4 main links use LTE-like numerology: 15 kHz spacing, FFT1024, about 72 samples of CP, roughly 600 active carriers, and a 5 ms / 200 Hz timing structure. Therefore, 5 ms periodicity alone does not identify DroneID.

Main video, control/C2, Wi-Fi/Bluetooth RID, and DJI DroneID require separate classification. High-duty-cycle main links are best handled with joint CP/ZC, bandwidth, and frame-structure analysis; a simple median-plus-MAD power threshold changes behavior with occupancy and baseline power.

## O4 packet findings

Observed O4 logical types include `AA`, `A7`, and `87`. AA and 87 associate through a four-byte hashcode. Third-party material describes A7 as an unencrypted information packet; the confirmed 87 decryption chain does not depend on A7.

Flight-state captures produced AA and same-hash 87 packets. Once a service returned the 16-byte note for AA, subsequent 87 packets decrypted locally. See [O4_CRYPTO_CHAIN.md](O4_CRYPTO_CHAIN.md).

Two 20 MS/s captures at different 2.4 GHz centers each produced a double-CRC-valid 87 after correct resampling. Sample-rate consistency is therefore a mandatory preflight check for ZC, CP, and CRC processing.

## O4 PHY boundary

Some captured O4 encrypted packets retain the classic 9-symbol root600/root147 shell and pass through the established O2 PHY/FEC chain into double-CRC-valid logical packets. Public discussion also reports a newer 10-symbol dynamic-root structure:

```text
Q Q Q | ZA ZA | ZB ZB | Q Q Q
```

Its six QPSK data symbols again produce 7,200 bits. This structure remains an end-to-end validation hypothesis; O4 models and protocol versions should be classified independently.

## AA/87 transmission conditions

Observed behavior and third-party service material suggest model-dependent transmission conditions. Some aircraft emit key packets after an indoor link is established, while newer models may require outdoor positioning and flight state before useful AA/87 transmission. Treat this as model- and firmware-specific behavior.

## Cryptanalytic boundary

- Standard SM2 retains roughly 128-bit generic security under a small set of known AA→note pairs.
- The complete AES-128 note keyspace contains `2^128` candidates.
- Fixed 87 plaintext fields provide an efficient verifier for a constrained key hypothesis.
- An aircraft-side SM2 public key identifies the hierarchy, key ID, and encryption call path; AA decryption uses the corresponding private key.

Promising implementation research includes low-entropy note derivation, C1 or nonce reuse, firmware key IDs and public keys, and legally obtained offline receiver implementations.

## Reproduction checklist

1. Cross-check the sample rate using the capture command, file size, and reported duration.
2. Record the actual center frequency and gain settings from the capture command.
3. Identify DroneID using CP, ZC, symbol count, and both CRCs together.
4. Record a ZC peak as a PHY candidate and a double-CRC result as a payload decode.
5. Label CRC-valid ciphertext as encrypted transport and preserve the original payload.
6. Attribute third-party terminology to its source and verify protocol claims independently.
7. Publish anonymized identifiers, locations, and credential fields.

## Recommended experiment artifacts

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

## Next research steps

- verify the standard SM2 KDF and C3 with additional independent sessions;
- locate the business public key and key ID in aircraft firmware;
- study legally obtained receivers with offline O4 parsing capability;
- implement stateful streaming resampling from 20 to 15.36 MS/s;
- add the 10-symbol dynamic-root O4+ detector as an independent pipeline;
- expand synthetic packet and unit-test coverage.
