# DJI OcuSync DroneID Research

[English](README.md) | [简体中文](README.zh-CN.md) | [Facts & evidence](FACTS.md)

Reproducible DJI OcuSync DroneID PHY, packet, and cryptographic analysis based on raw HackRF IQ captures.

**Updated 30 October 2026.** [Research status](STATUS.md) · [Evidence and sources](FACTS.md)

**The primary decryption approach presented publicly by this project is route 2: investigating predictability in the aircraft session key, not extracting the long-term AeroScope SM2 private key.** The research team reports successful private evaluation and broader potential; the applicable device scope and full implementation are not public.

## Decryption approach: route 2

Two approaches have been considered:

1. **Route 1 — hardware private key.** Extract the long-term recipient SM2 private scalar `d` from protected hardware. There is no public independently verifiable result.
2. **Route 2 — aircraft session key.** Investigate potentially fixed or predictable parts of the DroneID session key `K`, and the actual randomness of its remaining bytes. **This is the approach the project has chosen to describe publicly.**

The research team reports that route 2 has shown potential for broader use in private tests. The claim concerns key generation in particular implementations; it does not imply a flaw in SM2 or AES. No complete recovery implementation, key-distribution dataset, or cross-model validation has been published, so this is not yet a publicly reproducible dongle-free decoder and should not be generalized to all O4 devices.

The aircraft DroneID key `K` is distinct from the AeroScope host–dongle transport-session key.

## Current status

- Public protocol work documents SM2-wrapped CRYP session keys and AES-128-CTR INFP payloads. See the [protocol reference](https://github.com/EdwardBlair/dji-droneid-spec) and this repository's packet tools.
- The [public dongle demonstration](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456) concerns hardware-assisted decoding, not route 2 and not public extraction of the long-term private key.
- The newer [v3 RF/PHY specification](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY.md) uses an eight-symbol waveform and a seven-frequency schedule. This repository's existing scanner still uses a historic nine-symbol receiver baseline.

## Protocol baseline

The published protocol provides this reference model, used here as a baseline when evaluating route 2:

```text
aircraft
  AES-128 session key K (random in the protocol model)
  random SM2 ephemeral scalar k
       │
       ├─ C1 = kG
       ├─ S  = kQ              (Q = AeroScope recipient public key)
       └─ SM3 KDF masks K
              ↓
         AA / CRYP
              ↓  corresponding SM2 private scalar d
         session key K
              ↓
87 / INFP = AES-128-CTR(K, nonce8 || 0x00×8, telemetry)
```

Terminology:

| Observed name | Role |
|---|---|
| `AA`, ASCII `CRYP` | SM2-wrapped random AES session-key packet |
| `note` | 16-byte AES session key |
| `87`, ASCII `INFP` | AES-CTR-encrypted dynamic telemetry packet |
| `hashcode` / key identifier | 4-byte session association used to match CRYP and INFP in observed captures |

Key public confirmations:

- [CRYP carries the SM2-wrapped session key; INFP is AES-CTR telemetry](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205)
- [Detailed random-session-key + SM2 public-key construction](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928617113)
- [Complete Python reference decryptor requiring the SM2 private scalar](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887)
- [Full facts/evidence ledger](FACTS.md)

## Status

| Stage | Status | Evidence |
|---|---|---|
| HackRF signed-int8 IQ input | **LOCAL-VERIFIED** | Live capture and replay |
| Classic O2 PHY/FEC/CRC chain | **LOCAL-VERIFIED** | [decoder](src/o2_droneid_decode.py), [Turbo adapter](tools/remove_turbo_soft.c) |
| O4 AA/CRYP and 87/INFP recovery | **LOCAL-VERIFIED** | Double-CRC-valid captures |
| CRYP C1 on the SM2 curve and `C1‖C3‖C2` envelope | **LOCAL-VERIFIED + PUBLIC-CONFIRMED** | Local checks + [protocol confirmation](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205) |
| `note → INFP/87` AES-128-CTR | **LOCAL-VERIFIED** | Coherent sequential telemetry |
| Random session-key + SM2 wrapping (protocol baseline) | **PUBLIC-CONFIRMED** | [Issue #1 clarification](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928617113) |
| Complete decryptor given the correct SM2 private scalar | **PUBLIC** | [reference code](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |
| Route 2: session-key predictability | **Privately evaluated; details not released** | See [research status](STATUS.md); no public key samples or complete implementation |
| Relevant SM2 private scalar | **NOT PUBLICLY VERIFIED** | No independently verified public extraction in cited sources |
| AeroScope dongle as CRYP decryption oracle | **THIRD-PARTY DEMONSTRATION** | [King-Of-Knights console transcript](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456); USB command protocol and script not released |
| O4 key offer by TheOldCode | **CLARIFIED: ONLINE SERVICE ONLY, NOT SM2 PRIVATE KEY** | [Original](https://github.com/proto17/dji_droneid/issues/63#issuecomment-6057095721), [explicit correction](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6075832628) |
| Independent classification of vendor decryption method | **TEST CORPUS OFFERED, NOT YET TESTED** | [EdwardBlair proposal](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6062814886) |
| Third-party complete offline O4 implementation | **PUBLICLY REPORTED** | [online/offline resolved](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704941726), [decoded telemetry confirmed](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5705619316) |
| Remote-ID `root_key/CMAC/RIDkey` path as O4 DroneID key derivation | **CORRECTED / REJECTED** | [Remote ID correction](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5929240147), [DroneID does not use it](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656) |

## Publication scope

This repository describes **the findings and direction of route 2**, not its sensitive parameters, real session keys, traffic samples, or complete implementation. It is therefore not yet an independently reproducible software decryptor.

Route 1 remains relevant to understanding the protocol, but no public verifiable extraction of the AeroScope long-term SM2 private scalar has been established. Previously published dongle-assisted decoding is a separate method.

For source attribution and evidence limitations, see [FACTS.md](FACTS.md).

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

## HackRF scan frequency presets and hopping research

[Issue #2: Known DroneID frequencies](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/2) identified a missing **5816.5 MHz** receiver frequency. The scan code now offers **three documented frequency presets**, while retaining the original 2.4 GHz scan order and the existing custom `--freqs` override.

| `--preset` | Meaning | 2.4 / 5.8 GHz entries |
|---|---|---|
| `baseline` (default) | Previous repository scan order, now with 5816.5 MHz added to 5.8 GHz | 5 / 4 |
| `issue2` | King-Of-Knights' reported frequency list | 4 / 4 |
| `paper2022` | Bender's 2022 Table II, distinct entries only; **historical**, not an O4 frequency map | 5 / 7 |

```bash
# Passive 5.8 GHz scanning, including the newly added 5816.5 MHz
python3 src/droneid_hackrf_scanner.py --band 5g --preset baseline

# Use the separate Issue #2 frequency list on both bands
python3 src/droneid_hackrf_scanner.py --band both --preset issue2

# Compare against historical frequencies or force a custom centre frequency
python3 src/droneid_hackrf_scanner.py --band both --preset paper2022
python3 src/droneid_hackrf_scanner.py --freqs 2474.5
```

The 2022 paper's **2.4 GHz upper bound of 2474.5 MHz is prose-only**: its Table II instead repeats 2459.5 MHz. It is therefore not silently included in `paper2022`. In all cases `--freqs` overrides `--preset` and `--band`.

**Hopping evidence must stay model-scoped:** Mavic 2/Mini 2 measurements report ~640 ms transmissions in trains of 13 per frequency, whereas EdwardBlair describes a *newer/O4* 8-bit publication counter, modulo-256-before-modulo-seven lookup, and a 163.84 s supercycle. The **seven-lane lookup and counter formula are now published** in [the October v3 specification](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY.md). The scanner **does not implement the v3 eight-symbol PHY or phase following**, and `--dwell 0.80` is not hop synchronization. Historical `issue2` includes 2459.5 MHz, which [EdwardBlair excludes from the v3 seven-frequency set](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6490897000).

See [FACTS.md](FACTS.md) for per-model data, exact primary citations, and caveats. Do not merge the legacy/historical and newer/O4 lists into a supposedly universal frequency table.

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

- prioritize independent, privacy-preserving evaluation of route 2 across devices and firmware, without publishing live session keys or identifying location data;
- independently validate the public SM2 reference decryptor against sanitized CRYP/INFP test vectors when lawful key access is available;
- study the AeroScope upgrade dongle **host↔dongle interface** and public 2024 teardown at the protocol/interface level; do not assume a TEE without direct hardware evidence;
- independently check dongle-oracle claims and proposals for discriminating tests without requiring publication of confidential key material;
- cross-validate the O4/O4+ family claim across Air 3/3S, Mini 4 Pro, Avata 2, Mavic 4 Pro and enterprise models;
- document O4 PHY variants with end-to-end CRC-valid captures;
- determine the exact role of ZC root 147; current public discussion says root 600 alone is sufficient for O4 DroneID decoding;
- publish sanitized evidence for the observed Inspire 3/O3 encrypted-DroneID case;
- keep Remote ID KDF research separate from proprietary OcuSync DroneID;
- expand synthetic tests and anonymized cross-model test vectors.

See [FACTS.md](FACTS.md) for evidence status and exact citations.

## Publication and privacy

Examples should use synthetic or anonymized identifiers and locations. Do not publish private service credentials, session secrets, real serial numbers, exact operator/home coordinates, or acquisition metadata that can identify individuals.

## Responsible use

This project supports interoperability research, spectrum analysis, receiver development, and authorized security research. Use it only for passive reception and explicitly authorized testing in compliance with applicable radio, privacy, aviation, and computer-security law.

DJI, OcuSync, AeroScope, and related product names belong to their respective owners. This project is independent and is not affiliated with or endorsed by DJI or the referenced third parties.

## License

See [LICENSE](LICENSE).
