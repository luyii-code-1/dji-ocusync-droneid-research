# DJI OcuSync DroneID Research

[English](README.md) | [简体中文](README.zh-CN.md)

Reproducible DJI OcuSync O2/O4 DroneID research and tools based on raw HackRF IQ captures.

This repository consolidates findings verified as of **2026-08-27** through raw captures, CRC validation, and continuous telemetry. It covers the receive chain, physical layer, packet structure, and cryptographic envelope, with explicit confidence levels and open research steps.

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
docs/RESEARCH_NOTES.md      Complete evidence, experiments, and pitfalls
docs/O4_CRYPTO_CHAIN.md     AA/87 fields and cryptographic chain
docs/MEASUREMENTS.md        IQ statistics, formulas, correlations, and CRC values
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

## License

Original content in this repository is licensed under the [GNU General Public License v3.0](LICENSE). Third-party dependencies remain subject to their respective licenses.
