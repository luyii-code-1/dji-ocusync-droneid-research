# DJI OcuSync DroneID Research

[English](README.md) | [简体中文](README.zh-CN.md) | [Facts & evidence](FACTS.md)

Reproducible DJI OcuSync DroneID PHY, packet, and cryptographic analysis based on raw HackRF IQ captures.

**Updated 2026-10-08.** The repository now separates local reproduction from public third-party confirmation. The detailed claim-by-claim evidence ledger is in [FACTS.md](FACTS.md).

The current O4 conclusion is: CRYP contains a **random AES-128 session key wrapped with SM2**, and INFP contains **AES-128-CTR encrypted DroneID telemetry**. A complete public reference decryptor now exists for the standard path once the corresponding 256-bit SM2 private scalar is supplied. The outstanding boundary for a **publicly reproducible dongle-free decryptor** is still the corresponding SM2 private scalar (or an equivalently available authorized capability), not the packet format or AES layer. A third party has demonstrated dongle-mediated decryption in a public console transcript; no public independent private-key extraction has been verified.

## Confirmed result

For the O4 chain reproduced on Mini 5 Pro and independently confirmed in public discussion:

```text
aircraft
  random AES-128 session key K
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
| Random session-key + SM2 wrapping model | **PUBLIC-CONFIRMED** | [Issue #1 clarification](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928617113) |
| Complete decryptor given the correct SM2 private scalar | **PUBLIC** | [reference code](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |
| Relevant SM2 private scalar | **NOT PUBLICLY VERIFIED** | No independently verified public extraction in cited sources |
| AeroScope dongle as CRYP decryption oracle | **THIRD-PARTY DEMONSTRATION** | [King-Of-Knights console transcript](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456); USB command protocol and script not released |
| Direct O4 decryption-key availability | **UNVERIFIED CLAIM** | [TheOldCode offer](https://github.com/proto17/dji_droneid/issues/63#issuecomment-6057095721); key type not established |
| Independent classification of vendor decryption method | **TEST CORPUS OFFERED, NOT YET TESTED** | [EdwardBlair proposal](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6062814886) |
| Third-party complete offline O4 implementation | **PUBLICLY REPORTED** | [online/offline resolved](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704941726), [decoded telemetry confirmed](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5705619316) |
| Remote-ID `root_key/CMAC/RIDkey` path as O4 DroneID key derivation | **CORRECTED / REJECTED** | [Remote ID correction](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5929240147), [DroneID does not use it](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656) |

## What remains non-public

The algorithmic chain is publicly described well enough to implement. **A dongle-mediated CRYP → aircraft session key → INFP plaintext workflow has been reported with a console demonstration**, but its host-side USB protocol and code have not been published. The remaining gap for a **fully reproducible dongle-free** decoder is independently verified access to the corresponding SM2 private scalar or an equivalent disclosed mechanism.

Public evidence currently supports:

- AeroScope's upgrade hardware contains a USB decryption dongle with key material: [Aerial Defence / Edgesource security research](https://www.aerial-defence.com/security-risks-of-the-aeroscope-upgrade-module-whitepaper/).
- Edgesource's March 2024 [whitepaper, §1.5–1.6 / Figures 3–6](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf) documents a physical teardown (custom USB hub plus removed processor), AeroScope–dongle authentication and the encrypted transport session. **It does not establish that the dongle implements a TEE**, nor does the reused [photo in Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5944688781) prove a new 2026 teardown.
- Keep **AeroScope–dongle transport session key** separate from the **aircraft DroneID session key**: the dongle unwraps CRYP and supplies the latter to the AeroScope host, which then decrypts INFP. [Edgesource 2024, Figure 5–6](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf).
- EdwardBlair describes material extraction from the dongle as the remaining key-material approach: [comment](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948750307).

This repository does **not** claim that the private scalar has been publicly extracted. The [reported O4 key offer](https://github.com/proto17/dji_droneid/issues/63#issuecomment-6057095721) does not disclose the key type or include independent cryptographic proof. [EdwardBlair offered a test corpus](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6062814886) to distinguish dongle use, private-key possession and other mechanisms; no public validation result is shown in that comment.

Also note the corrected dead-end: the previously discussed `root_key → CMAC → RIDkey` construction belongs to **Remote ID/internal controller telemetry protection**, not OcuSync DroneID. See [FACTS.md](FACTS.md#3-corrected-interpretation-remote-id-kdf-is-not-droneid).

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
