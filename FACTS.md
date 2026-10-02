# DJI OcuSync DroneID — Facts and Evidence

[English](FACTS.md) | [简体中文](FACTS.zh-CN.md)

**Last reviewed: 2026-10-02**

This document separates **locally reproduced facts**, **independent public confirmations**, **third-party implementation claims**, **corrected/red-herring paths**, and **open questions**. A cited discussion claim is not treated as equivalent to a locally reproducible result.

## Evidence labels

- **LOCAL-VERIFIED** — reproduced from captures/tools in this repository.
- **PUBLIC-CONFIRMED** — independently stated in public technical discussion and consistent with local evidence.
- **PUBLIC-CLAIM** — a third party publicly reports an implementation/result, but the implementation or key material is not public.
- **OBSERVED-NOT-UNIVERSAL** — observed on specific hardware/firmware; do not generalize without cross-validation.
- **CORRECTED** — an earlier interpretation was later contradicted or scoped to a different protocol.
- **OPEN** — not publicly resolved.

## 1. O4 packet and crypto chain

| Fact | Status | Evidence |
|---|---|---|
| O4 logical packets observed by this project include `AA/CRYP` and `87/INFP`. Matching packets share a 4-byte session identifier/hash. | **LOCAL-VERIFIED** | [Local packet tooling](src/o4_packet_tool.py), [project cross-validation thread](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1) |
| `CRYP` carries the AES session key wrapped with SM2; `INFP` carries AES-CTR encrypted telemetry. | **LOCAL-VERIFIED + PUBLIC-CONFIRMED** | [Independent confirmation by EdwardBlair](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205) |
| The aircraft generates a random 128-bit AES session key for INFP, chooses an SM2 ephemeral scalar `k`, computes `C1=kG` and shared point `S=kQ` using the AeroScope recipient public key `Q`, then masks the session key with the SM3 KDF in CRYP. | **PUBLIC-CONFIRMED** | [Detailed clarification](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928617113) |
| A valid CRYP packet contains a standard-SM2-compatible `C1 || C3 || C2` structure; this project's samples have a 64-byte raw EC point, 32-byte C3, and 16-byte C2/session-key plaintext length. | **LOCAL-VERIFIED + PUBLIC-CONFIRMED** | [Local implementation](src/o4_packet_tool.py), [public protocol confirmation](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704860205) |
| INFP uses AES-128-CTR with the recovered session key. For this project's captures the IV construction is `nonce8 || 0x00*8`. | **LOCAL-VERIFIED** | [Local implementation](src/o4_packet_tool.py), [tests](tests/test_o4_packet_tool.py) |
| One recovered session key decrypts multiple same-session INFP packets into coherent sequential telemetry. | **LOCAL-VERIFIED** | [Repository README research record](README.md), [published project update](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5636317132) |
| A complete Python reference implementation for `SM2 private scalar -> CRYP session key -> INFP plaintext` was posted publicly. | **PUBLIC-CONFIRMED** | [Reference implementation posted by EdwardBlair](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |
| That reference implementation requires a 32-byte / 256-bit SM2 private scalar and validates C3 and a 4-byte key identifier before decrypting INFP. | **PUBLIC-CONFIRMED** | [Same reference implementation](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |

Conceptual chain:

```text
aircraft:
  random AES-128 session key K
  random SM2 scalar k
  C1 = kG
  S  = kQ
  mask = SM3-KDF(S)
  CRYP = SM2_Encrypt(Q, K)

receiver:
  S = dC1
  K = SM2_Unwrap(d, CRYP)
  INFP plaintext = AES-128-CTR(K, nonce8 || 0x00*8, ciphertext)
```

Here `Q` is the recipient/AeroScope public key and `d` is the corresponding private scalar.

## 2. What is and is not public about the key

| Fact | Status | Evidence |
|---|---|---|
| The protocol and decryption algorithm are now publicly described well enough to implement a decryptor **if the correct SM2 private scalar is available**. | **PUBLIC-CONFIRMED** | [Reference decryptor](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887) |
| The corresponding SM2 private key itself is not published in this repository or in the cited public discussion. | **OPEN** | [Cross-validation thread](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1) |
| AeroScope's upgrade hardware includes a USB decryption dongle containing key material. | **PUBLIC-CONFIRMED** | [Aerial Defence / Edgesource whitepaper page](https://www.aerial-defence.com/security-risks-of-the-aeroscope-upgrade-module-whitepaper/) |
| Public discussion points to the AeroScope dongle as the remaining key-material target for a fully independent implementation. | **PUBLIC-CLAIM** | [EdwardBlair: material extraction from the dongle is the remaining approach](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948750307) |
| The dongle/TEE communication path is documented by the 2024 AeroScope Upgrade Module security research. | **PUBLIC-CONFIRMED** | [Pointer in Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928949673), [whitepaper page](https://www.aerial-defence.com/security-risks-of-the-aeroscope-upgrade-module-whitepaper/) |

This repository **does not claim that the SM2 private scalar has been publicly extracted**.

## 3. Corrected interpretation: Remote ID KDF is not DroneID

An earlier Issue #1 branch discussed:

```text
K_mid  = CMAC(root_key, 01 || "DJI DRONES" || 00 || "SASE" || 80)
RIDkey = CMAC(K_mid,    01 || "DEC KEY"   || 00 || "DJI RID" || 80)
```

That construction should **not** be presented as the OcuSync DroneID CRYP/INFP key derivation.

| Fact | Status | Evidence |
|---|---|---|
| The CMAC construction above was reported as a DJI RID/Remote ID-related KDF. | **PUBLIC-CLAIM** | [Original KDF comment](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5772131999) |
| EdwardBlair explicitly corrected the discussion: this KDF is for Remote ID and is distinct from DroneID. | **CORRECTED** | [Correction](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5929240147) |
| He further described the RID key as protecting controller GPS/telemetry on the controller-to-aircraft internal path before the aircraft emits unencrypted Wi-Fi/Bluetooth Remote ID. | **PUBLIC-CONFIRMED (discussion)** | [Explanation](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5929968912), [final clarification](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656) |
| OcuSync DroneID does **not** use that RID CMAC mechanism. | **PUBLIC-CONFIRMED** | [Final clarification](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656) |

Therefore the current project model is **SM2-wrapped random session key**, not `root_key -> CMAC -> RIDkey -> INFP`.

## 4. O4/O4+ model scope

| Fact | Status | Evidence |
|---|---|---|
| This repository's end-to-end local capture/decode work was performed on DJI Mini 5 Pro. | **LOCAL-VERIFIED** | [README](README.md) |
| EdwardBlair states that the same O4/O4+ DroneID mechanism is identical across Air 3 onward, including enterprise models. | **PUBLIC-CONFIRMED (attributed)** | [Issue #1 comment](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5716672326) |
| Because the cross-model statement is third-party confirmation rather than this repository's own capture set, per-model captures are still valuable for independent validation. | **OPEN / research practice** | [Cross-validation issue](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1) |

## 5. PHY/FEC facts

### Classic O2 baseline — locally reproduced

```text
sample rate       15.36 MS/s
FFT               1024
subcarrier space  15 kHz
active carriers   600 (DC excluded)
symbols           9
normal CP         72
long CP           80
ZC                 root 600 / root 147
data symbols      6 QPSK symbols
soft bits         7200
LTE Turbo         K=1408, D=1412
transport         176 bytes
validation        CRC24A + DJI CRC16
```

Evidence: [classic decoder](src/o2_droneid_decode.py), [Turbo adapter](tools/remove_turbo_soft.c).

### O4 observations

| Fact | Status | Evidence |
|---|---|---|
| Some encrypted O4 DroneID captures in this project can be recovered through a classic DJI/O2-like 9-symbol PHY/FEC shell and validated with both CRCs. | **LOCAL-VERIFIED** | [RUB DroneSecurity cross-validation post](https://github.com/RUB-SysSec/DroneSecurity/issues/50#issuecomment-5636324901) |
| For current O4 DroneID, EdwardBlair states root 600 is sufficient for decoding; root 147 is consistently present but is not required. | **PUBLIC-CONFIRMED (attributed)** | [Issue #1 comment](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5716726564) |
| The purpose/origin of root 147 in the current O4 waveform remains unresolved; a possible C2 relation was suggested but not established. | **OPEN** | [Same comment](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5716726564) |
| An Air 3S O4 user has publicly reported a recurring ~500 µs / four-ZC burst; its exact relation to DroneID versus another O4/control-state frame remains unresolved. | **OBSERVED-NOT-UNIVERSAL** | [RUB DroneSecurity Issue #50](https://github.com/RUB-SysSec/DroneSecurity/issues/50) |

The repository should not state that every O4 frame uses one universal shell until cross-model/firmware captures establish that.

## 6. Transmission behavior

### Mini 5 Pro

Local captures in this project observed:

- CRYP/AA key material after valid GNSS positioning.
- INFP/87 dynamic telemetry after start/takeoff.
- same-session CRYP and INFP sharing the session identifier/hash.

This behavior is **model/firmware-specific observation**, not a universal trigger rule.

### Public DragonSDR documentation

DragonSDR/WarDragon documentation currently states that O4 DroneID is only present when motors are spinning, while power-on alone activates the OcuSync control link. Treat this as a product-documentation statement and cross-check per model.  
Sources: [DragonSDR README](https://github.com/alphafox02/dragonsdr_dji_droneid), [WarDragon DragonSDR docs](https://github.com/alphafox02/WarDragon/blob/main/docs/hardware/dragonsdr.md).

## 7. Open-source and commercial receiver status

| System | Publicly documented capability | Evidence |
|---|---|---|
| DragonSDR open-source receiver | O2/O3 full telemetry; O4 detection gives session hash ID, frequency, RSSI. | [DragonSDR README](https://github.com/alphafox02/dragonsdr_dji_droneid) |
| DragonScope | Adds O4 serial, aircraft/pilot/home GPS, altitude, speed; current public setup requires a license/config and internet connectivity. | [DragonSDR README — DragonScope section](https://github.com/alphafox02/dragonsdr_dji_droneid), [WarDragon architecture](https://github.com/alphafox02/WarDragon/blob/main/docs/architecture/overview.md) |
| alphafox02 private implementation | Publicly reports end-to-end O4 complete decoding with both online and offline solutions, but does not publish that proprietary implementation. | [Online/offline resolved](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5704941726), [confirmed as decoded telemetry](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5705619316) |
| AntSDR old repository | Maintainer stated the old repository would be retired in favor of `dragonsdr_dji_droneid`. | [Migration comment](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5883226434) |

Important distinction: the existence of a private offline decoder establishes **implementation existence**, not a public reproducible key-recovery method.


### Historical implementation clue: "<=100 candidates"

EdwardBlair also stated in the older AntSDR discussion that, after inferring alphafox02 did not possess the key, he recognized the implementation approach and had reduced "that particular problem" to constant-time plus binary search over at most about 100 candidates, avoiding multi-second first-packet processing. The candidate object and algorithm were **not disclosed**. This statement therefore does **not** establish that SM2, the 256-bit private scalar, or the 128-bit AES session key has a ~100-element keyspace.

Status: **PUBLIC-CLAIM / mechanism undisclosed**.  
Source: [AntSDR Issue #27 comment](https://github.com/alphafox02/antsdr_dji_droneid/issues/27#issuecomment-5716952989).

## 8. O2/O3 scope

- This repository has a reproducible classic O2 plaintext DroneID PHY/FEC chain.
- Do **not** assume every O3 platform is plaintext solely because older O2/O3 implementations were.
- An Inspire 3/O3 encrypted-DroneID observation has been reported by the repository owner, but it has not yet been independently cross-validated or documented with a public sanitized capture in this repository. Treat it as **OBSERVED-NOT-YET-PUBLISHED**, not as a universal O3 conclusion.
- DragonSDR's current public matrix labels its supported O2/O3 examples as fully decoded and O4 as encrypted/detection-only without DragonScope; that matrix is a product-support statement rather than a proof that all O3 products use one protocol behavior. [DragonSDR README](https://github.com/alphafox02/dragonsdr_dji_droneid)

## 9. Packet terminology and current parser model

From current public discussion/reference code:

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

The exact offsets depend on whether the input is the direct core packet, an outer logical envelope, or the V1 service frame. See the public reference parser for envelope handling and layout checks: [Issue #1 reference implementation](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5928889887).

## 10. What is solved vs. open

### Solved / public enough to implement

- O2 classic PHY/FEC/CRC chain.
- O4 CRYP/INFP packet roles.
- SM2 wrapping model.
- SM3 KDF/C3 verification logic.
- AES-128-CTR INFP decryption once the session key is known.
- A complete reference decoder once the correct SM2 private scalar is supplied.
- O4 detection in public DragonSDR software.

### Still open publicly

- Public recovery/extraction of the AeroScope SM2 private scalar.
- A public, independently reproducible dump/oracle workflow for the dongle key.
- Complete cross-model PHY validation for all O4/O4+ frame variants.
- Definitive explanation of root 147's role in current O4 DroneID.
- Public cross-validation of encrypted Inspire 3/O3 captures.
- Public offline DragonScope-equivalent implementation without proprietary key material.

## 11. Source index

Primary technical discussion:

- [Project cross-validation Issue #1](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1)
- [AntSDR Issue #27 — O4 decryption key](https://github.com/alphafox02/antsdr_dji_droneid/issues/27)
- [RUB-SysSec DroneSecurity Issue #50 — Air 3S O4 PHY](https://github.com/RUB-SysSec/DroneSecurity/issues/50)
- [proto17/dji_droneid Issue #50 — OcuSync 4](https://github.com/proto17/dji_droneid/issues/50)

Current receiver ecosystem:

- [DragonSDR DJI DroneID Receiver](https://github.com/alphafox02/dragonsdr_dji_droneid)
- [WarDragon](https://github.com/alphafox02/WarDragon)
- [WarDragon DragonSDR hardware docs](https://github.com/alphafox02/WarDragon/blob/main/docs/hardware/dragonsdr.md)

AeroScope dongle:

- [Aerial Defence: Security Risks of the AeroScope Upgrade Module](https://www.aerial-defence.com/security-risks-of-the-aeroscope-upgrade-module-whitepaper/)

Local reproducible code:

- [O4 packet tool](src/o4_packet_tool.py)
- [O4 tests](tests/test_o4_packet_tool.py)
- [O2 decoder](src/o2_droneid_decode.py)
- [HackRF scanner](src/droneid_hackrf_scanner.py)
- [TurboFEC adapter](tools/remove_turbo_soft.c)

## 12. Citation policy for future updates

When adding a new conclusion:

1. Prefer raw IQ + reproducible CRC/plaintext evidence.
2. Link the exact public comment/commit/paper that supports third-party claims.
3. Attribute third-party universal statements rather than silently converting them into local verification.
4. Keep Remote ID and proprietary OcuSync DroneID separate.
5. Mark commercial/private implementation claims as claims unless code/test vectors are public.
6. If a prior interpretation is corrected, preserve the correction and source so the old path does not reappear.
