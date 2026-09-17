# DJI OcuSync DroneID Research

[English](README.md) | [简体中文](README.zh-CN.md)

Reproducible DJI OcuSync DroneID PHY, packet, and cryptographic analysis based on raw HackRF IQ captures.

**Updated 2026-09-17.** The O4 AA/87 cryptographic relationship is no longer treated here as a hypothesis. Local packet measurements, successful telemetry decryption, and independent public confirmation now establish the protocol role of the two packet families.

## Confirmed result

For the tested DJI Mini 5 Pro O4 implementation:

```text
HackRF IQ
  → ZC / OFDM / Turbo
  → CRC24A + DJI CRC16
  → logical packets

AA / CRYP
  → SM2-wrapped 16-byte session key (note)
  → requires corresponding SM2 private key or equivalent decryptor

87 / INFP
  → AES-128-CTR
  → key = note
  → IV = nonce8 || 0x00 × 8
  → SN / UUID / aircraft / pilot / home telemetry
```

The important terminology is now:

| Observed byte/type name | Protocol role |
|---|---|
| `AA`, ASCII `CRYP` | SM2-wrapped session-key packet |
| `note` | 16-byte AES session key |
| `87`, ASCII `INFP` | AES-CTR-encrypted dynamic telemetry packet |
| `hashcode` | 4-byte session association shared by matching CRYP/INFP packets |

This mapping was independently confirmed publicly in `alphafox02/antsdr_dji_droneid` Issue #27: CRYP contains the SM2-wrapped session key and INFP contains the corresponding AES-CTR-encrypted telemetry. The same discussion also states that complete online and offline decoding has been implemented privately, although that implementation and key material are not public.

Public references:

- [Protocol confirmation: CRYP = SM2-wrapped session key, INFP = AES-CTR telemetry](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205)
- [Private implementation reports both online and offline decoding resolved](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704941726)
- [Clarification that this means completely decoded telemetry](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5705619316)

## Status

| Stage | Status | Evidence |
|---|---|---|
| HackRF signed-int8 IQ input | **Verified** | Live capture and replay |
| Classic O2 9-symbol OFDM / ZC600+147 | **Verified** | Correlation, frame structure, CRC recovery |
| O2 LTE Turbo transport | **Verified** | CRC24A remainder = 0 |
| O2 inner logical payload | **Verified** | DJI CRC16 remainder = 0 |
| O4 AA/CRYP and 87/INFP logical packets | **Verified** | Double-CRC-valid captures |
| AA/CRYP C1 point on standard SM2 curve | **Verified** | Multiple independent sessions |
| AA/CRYP `C1‖C3‖C2` envelope | **Confirmed** | Local structure + independent public confirmation |
| `note → 87/INFP` | **Verified** | AES-128-CTR gives coherent sequential telemetry |
| `AA/CRYP → note` protocol role | **Confirmed** | SM2-wrapped session key |
| Local `AA/CRYP → note` execution without private key | **Not available in this repository** | Requires the corresponding private key or equivalent decryptor |
| Third-party complete offline O4 decode | **Publicly reported** | Implementation/key material not published |

## What remains non-public

The protocol is now substantially understood. The remaining practical barrier to a fully independent offline decoder is not the AES layer or packet format; it is access to the SM2 unwrapping capability.

The following are still non-public in the material available to this project:

- the corresponding SM2 private key material;
- how that key is provisioned or protected in commercial/offline receivers;
- whether all O4/O4+ products share one key hierarchy or use multiple key IDs;
- a public equivalent local CRYP decryptor;
- reproducible public test vectors that perform `CRYP → session key` without an external service.

This repository does **not** claim that the private key itself has been publicly recovered.

## Tested aircraft and transmission behavior

### DJI Mini 5 Pro / O4

Observed behavior:

- CRYP/AA key-material packets begin after valid GPS/GNSS positioning.
- INFP/87 dynamic telemetry begins after the operator starts/takes off.
- CRYP and same-session INFP packets share a four-byte `hashcode`.
- A session refresh or aircraft restart changes the session association and requires the corresponding new session key.

### O2 and O3 scope

Do not treat “O2/O3” as one universal plaintext behavior.

Classic O2 captures in this project use the known plaintext DroneID chain. However, encrypted DroneID has also been observed on at least one O3 platform, **DJI Inspire 3**. Therefore the older statement that O3 as a whole broadcasts plaintext DroneID is no longer valid.

The exact relationship between Inspire 3 O3 encryption and the O4 CRYP/INFP chain should be validated per model and firmware before claiming identical cryptographic internals.

## Repository layout

```text
src/o4_packet_tool.py       Inspect CRYP/AA structure and decrypt INFP/87 with a known note
src/o2_droneid_decode.py    Classic O2 PHY/FEC reference decoder
src/droneid_hackrf_scanner.py
                            HackRF live/replay scanner
tools/remove_turbo_soft.c   TurboFEC adapter
```

## Quick start

Requirements: Python 3.10+ and OpenSSL command line.

Inspect an AA/CRYP packet:

```bash
python3 src/o4_packet_tool.py '<complete-AA-hex>'
```

Decrypt a same-session 87/INFP packet when the 16-byte session key is already known:

```bash
python3 src/o4_packet_tool.py --note '<16-byte-note-hex>' '<complete-87-hex>'
```

The current public tool intentionally covers packet validation and the known-session-key AES step. It does not contain DJI/private commercial SM2 key material.

## Packet relationship

Matching packets share the same session hash:

```text
CRYP/AA(hash=H) → session key K

INFP/87(hash=H, nonce=N1) → AES-CTR(K, N1 || 0x00×8)
INFP/87(hash=H, nonce=N2) → AES-CTR(K, N2 || 0x00×8)
INFP/87(hash=H, nonce=N3) → AES-CTR(K, N3 || 0x00×8)
...
```

A single recovered note was verified against multiple sequential INFP/87 packets. The resulting sequence numbers, timestamps, coordinates, and altitude values changed coherently, establishing that `note` is the session key rather than a packet-specific key.

## Common logical-packet header

```text
offset  size  meaning
0       1     packet_length_minus_3
1       1     message type / subtype
2       4     ASCII marker (`CRYP`, `INFP`, ...)
6       4     hashcode
...     ...   type-specific body
last-2  2     DJI CRC16, little-endian
```

Logical length is `packet[0] + 3`.

DJI CRC16 uses initial value `0x3692` with reflected polynomial `0x8408`. A valid complete logical packet has zero remainder.

## CRYP / AA structure

Observed AA packets begin with:

```text
AA 13 43 52 59 50 [hashcode]
      C  R  Y  P
```

The key-material region is:

```text
offset    size  interpretation
10:74     64    C1 = X || Y, two 32-byte big-endian coordinates
74:106    32    C3
106:122   16    C2; plaintext length equals the 16-byte session key
122:...   ...   remaining protocol fields / tail data
```

C1 values from multiple independent sessions satisfy the standard SM2 curve equation:

```text
p = FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
a = FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
b = 28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93
```

The repository's local packet evidence originally identified the `64 + 32 + 16` structure as raw-point SM2 `C1‖C3‖C2`. Independent public confirmation now identifies CRYP explicitly as an SM2-wrapped session-key packet.

Conceptually:

```text
S    = d × C1
mask = SM2_KDF(S.x || S.y, 16)
note = C2 XOR mask
C3   = SM3(S.x || note || S.y)
```

where `d` is the corresponding private key. The repository does not provide `d`.

## INFP / 87 encryption

The observed dynamic telemetry encryption is:

```text
cipher = AES-128-CTR
key    = note
IV     = nonce8 || 0x00×8
```

With a correct same-session note, the payload decrypts into stable DroneID field structure and coherent sequential telemetry.

## PHY and FEC baseline

### Classic O2 frame

```text
sample rate       15.36 MS/s
FFT               1024
subcarrier space  15 kHz
active carriers   600, DC excluded
symbols           9
normal CP         72
long CP           80
symbol index 3    ZC root 600
symbol index 5    ZC root 147
data symbols      1,2,4,6,7,8
```

FEC chain:

```text
6 QPSK symbols × 600 carriers × 2 bits = 7200 soft bits
→ Gold descramble
→ LTE reverse rate matching, E=7200, RV=0
→ LTE Turbo, K=1408, D=1412
→ 176-byte transport
→ CRC24A
→ logical payload
→ DJI CRC16
```

A decode is accepted only when both CRC24A and DJI CRC16 validate.

### O4 PHY boundary

Some captured encrypted O4 packets retain the classic 9-symbol root600/root147 shell and pass through the established O2 PHY/FEC pipeline into valid encrypted logical packets.

A newer 10-symbol dynamic-root structure has also been publicly discussed:

```text
Q Q Q | ZA ZA | ZB ZB | Q Q Q
```

That structure must still be validated end-to-end per aircraft/firmware before being treated as universal O4/O4+ behavior.

## Sample-rate requirement

HackRF raw files are interleaved signed-int8 I/Q:

```text
I0 Q0 I1 Q1 ...
2 bytes / complex sample
```

For a 20 MS/s capture, the classic 15.36 MS/s detector requires:

```text
20.00 MS/s × 96 / 125 = 15.36 MS/s
```

Using the wrong sample rate changes the ZC time scale, CP/FFT placement, CFO estimate, and downstream CRC result. Sample-rate consistency is therefore a mandatory validation step.

## Evidence rules

The project uses the following evidence order:

```text
raw IQ
> locally reproduced double-CRC result
> locally reproduced plaintext telemetry
> independent primary/public protocol confirmation
> public code
> discussion claims
> hypothesis
```

Accordingly:

- signal energy alone is not DroneID;
- a ZC/CP match is a PHY candidate, not a decoded payload;
- CRC24A validates the transport block;
- DJI CRC16 validates the logical packet boundary/content;
- valid encrypted packets remain ciphertext until the crypto step is reproduced;
- a third party saying it has an offline decoder establishes implementation existence, but not a public reproducible method.

## Reproduction checklist

1. Record actual sample rate, center frequency, and gains.
2. Verify the capture duration from file size and complex-sample format.
3. Identify candidate frames using CP/ZC and frame timing.
4. Require CRC24A and DJI CRC16 before accepting a logical packet.
5. Preserve original ciphertext and session hash.
6. For INFP/87 tests, preserve nonce and note provenance.
7. Publish only sanitized identifiers, locations, and metadata.

Recommended intermediate artifacts:

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

## Current research priorities

- cross-validate CRYP/INFP layouts across Air 3/3S, Mini 4 Pro, Avata 2, Mavic 4 Pro, Inspire 3, and other O3/O4 platforms;
- identify key IDs and public-key hierarchy across firmware generations;
- determine whether Inspire 3 O3 uses the same CRYP/INFP cryptographic chain or only a related encrypted transport;
- document the newer O4/O4+ PHY variants with double-CRC-valid end-to-end captures;
- study legally obtained offline receivers and commercial modules at the interface/protocol level without publishing protected credentials;
- expand synthetic tests and anonymized cross-model test vectors.

## Publication and privacy

Examples should use synthetic or anonymized identifiers and locations. Do not publish private service credentials, session secrets, real serial numbers, exact operator/home coordinates, or acquisition metadata that can identify individuals.

## Responsible use

This project supports interoperability research, spectrum analysis, receiver development, and authorized security research. Use it only for passive reception and explicitly authorized testing in compliance with applicable radio, privacy, aviation, and computer-security law.

DJI, OcuSync, AeroScope, and related product names belong to their respective owners. This project is independent and is not affiliated with or endorsed by DJI or the referenced third parties.

## License

See [LICENSE](LICENSE).
