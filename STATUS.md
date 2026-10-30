# DJI DroneID research status — 30 October 2026

[English](STATUS.md) | [简体中文](STATUS.zh-CN.md) | [Evidence ledger](FACTS.md) | [Home](README.md)

**The primary decryption approach presented publicly by this project is route 2: investigating predictability in the aircraft's session key.** The research team reports private validation and broader potential, but no complete implementation or independent cross-device evidence has been released. This page separates reproducible results, public references and unpublished findings.

## Research status

| Component | Status as of 2026-10-30 | Evidence / boundary |
|---|---|---|
| Classic v2/O2 DroneID PHY, turbo/FEC, CRC | **REPO-REPRODUCED** | [O2 decoder](src/o2_droneid_decode.py), [Turbo adapter](tools/remove_turbo_soft.c); historic **9-symbol** baseline |
| O4 CRYP / INFP-10 / INFP-11 packet & crypto chain | **PUBLIC-SPEC + local packet observations** | [EdwardBlair specification](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/README.md), [reference code](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/droneid.py), [local packet tool](src/o4_packet_tool.py) |
| V3/newer DroneID RF/PHY | **PUBLIC-SPEC; not yet integrated into local classic scanner** | [RF_PHY.md](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY.md) specifies **8 OFDM symbols**, **173-byte payload** plus CRC24A, 15.36 MS/s; do not identify as the local O2 nine-symbol PHY |
| Full O4 decode using **real AeroScope dongle** | **PUBLIC-REPORT; OWNER-REPORTED EXPERIENCE** | [King-Of-Knights dongle console demonstration](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456); [owner's public report of offline decoding based on that research](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078335828). Independent USB command protocol and reproducible source remain non-public |
| **Route 2: session-key predictability (public research focus)** | **Privately evaluated; not publicly reproducible** | Some implementations reportedly have predictable elements in `K`; device coverage and the full method are not published |
| Recovering real recipient SM2 private scalar `d` | **OPEN** | Neither this repo nor [the public spec (dummy test keys only)](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454/keys) publishes the real scalar. A dongle that unwraps CRYP does not expose `d` |
| Publicly reproducible dongle-free decoder | **OPEN** | Route 2 has no published independent implementation; standard SM2 reference code requires a valid key |
| Unencrypted startup DroneID in O4 | **DISPUTED / NOT REPRODUCED** | [Issue #3: a Mavic 4 Pro startup plaintext report](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3#issuecomment-6459214434); [EdwardBlair requests exact firmware](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3#issuecomment-6459273901). Do not generalize to all O4 |

## Findings from route 2

The first approach centered on extracting the long-term SM2 private key from secure hardware. **The project's main publicly described decryption approach is instead route 2:** studying fixed or predictable parts of the aircraft DroneID session key `K` and the randomness of the remaining bytes.

On 30 October 2026 the team reported that this approach had shown potential for broader use in private tests. This concerns key generation in particular implementations, not a weakness in SM2 or AES themselves. The public protocol still describes a random AES-128 key as its reference model.

**What is public is a description of the approach and the finding, not a complete reproducible decoder.** Sensitive parameters, real session keys and raw session records are not released. Device and firmware applicability requires further verification. The aircraft key `K` is distinct from the AeroScope host–dongle transport key.

## Related public research

The [Issue #1 hardware-assisted demonstration](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456) uses a real dongle to unwrap CRYP. It is not route 2, and its independent code was not released.

The [2024 Edgesource paper](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf) documents the upgrade-module hardware and protocol. Private conversations, identity links and hardware imagery without publication permission are omitted.

## Published protocol baseline

```text
Aircraft:
  16-byte AES key K (random in the published protocol model)
       ├─ key_id = SHA-256(K)[0:4]
       ├─ CRYP: SM2_Encrypt(Q, K) -> C1 || C3 || C2
       ├─ CRYP auxiliary AES-128-CTR ciphertext
       └─ INFP-10 / INFP-11 AES-128-CTR ciphertext

Receiver with correct recipient private key d:
  C1 -> shared EC point -> SM3 KDF/C3 check -> K
  check SHA-256(K)[0:4] == key_id
  decrypt CRYP auxiliary and same-session INFP

Hardware-assisted receiver:
  valid CRYP -> AeroScope dongle -> 16-byte K -> AES-CTR plaintext
  (private scalar d stays inside hardware; the host↔dongle transport key
   is a *different* session key)
```

Sources: [O4 protocol & known-session-key verification](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/README.md), [reference round-trip with **dummy** key d=1](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/EXAMPLE.md), [Edgesource host/dongle research](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf).

**TheOldCode correction:** Their earlier [offer of an “O4 decryption key”](https://github.com/proto17/dji_droneid/issues/63#issuecomment-6057095721) was subsequently [clarified as a key for an online decryption service, **not the SM2 private key**](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6075832628). Do not cite that offer as evidence that the AeroScope private scalar has been extracted.

**Remote ID distinction:** The `root_key → CMAC → RIDkey` discussion concerns the separate DJI Remote ID/controller channel, **not** the proprietary OcuSync DroneID CRYP/INFP scheme. [Correction](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5948725656).

## V3 RF/PHY and the local scanner

A new [public reference specification](https://github.com/EdwardBlair/dji-droneid-spec) (commit `55bb886`, 22 October 2026) defines the **newer v3 DroneID** waveform and RF schedule:

- Seven centres (MHz): **2414.5, 2429.5, 2444.5, 5756.5, 5776.5, 5796.5, 5816.5**. **2459.5 MHz is excluded** for v3, according to [EdwardBlair's explicit follow-up](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6490897000). Older hardware and other publications may use other frequencies.
- Schedule: publication every **640 ms**, 8-bit counter `c`, `r=(c+255)%256`, `i=(r+6)%7`; `frequency_mhz=[2429.5,2444.5,5756.5,5776.5,5796.5,5816.5,2414.5][i]`. Supercycle **256×640 ms = 163.84 s**. This exact published map supersedes the prior “lookup not yet public” statement.
- v3 PHY: **8** OFDM symbols per burst, 15.36 MS/s, FFT 1024, 600 occupied bins, 6 QPSK data symbols and two ZC reference symbols (root 600 at symbol 2, root 147 at symbol 4), **8,784 samples**; FEC output contains a **173-byte logical transport block plus CRC24A**. [Complete PHY](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY.md).
- The scanner in [src/droneid_hackrf_scanner.py](src/droneid_hackrf_scanner.py) still uses the older **9-symbol reference shell** and has frequency presets `baseline`, `issue2` and `paper2022`. These were created from historically different observations and **must not** be relabeled as verified v3 PHY or its seven-centre hopping follower. No v3 follower has been integrated into the repository.
- EdwardBlair reports this schedule reproduced on **Air 3S, Avata 2, Neo, Neo 2 and Mavic 3 Thermal**; that remains an **attributed report** pending independent raw-IQ reproduction here. [Report](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078283920).
- No 5.2 GHz DroneID frequency was found in that published v3 schedule; regulatory and firmware variation remain possible research questions, **not** permission to treat unspecified bands as verified. [Discussion](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078283920).

**Important:** The local project's older 9-symbol CRC-valid captures and v3 spec's 8-symbol frame should be described **separately**. They are not interchangeable. The specific PHY used by every previously collected O4 capture must be determined from its own raw IQ before declaring a contradiction or universal behavior.

## Verification evidence and remaining work

- A third-party [report](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-6478170923) states that 119 public transport blocks (12 CRYP, 93 INFP-10, 14 INFP-11) pass both CRCs under a shared key identifier. **Those packets have not had their real session independently decrypted** according to the same comment.
- EdwardBlair has published a protocol parser, synthetic/dummy private-key round-trip tests and [public synthetic validation material](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454/tests). These verify the *algorithm*, not possession of the genuine AeroScope recipient private key.
- Subsequent route 2 publications should use anonymized statistical results, device/firmware scope, and synthetic test vectors. Real session keys, sensitive flight tracks, credentials and private correspondence should remain outside the public repository.
- Hardware reverse engineering remains a separate research subject, not the project's main public decryption approach.

## Primary sources

- [Own Issue #1: crypto and dongle](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1)
- [Own Issue #2: frequencies](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/2)
- [Own Issue #3: disputed startup plaintext](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3)
- [EdwardBlair protocol spec (22 Oct 2026)](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454)
- [proto17 Issue #60: receiver and hop research](https://github.com/proto17/dji_droneid/issues/60)
- [Edgesource 2024 hardware paper](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)
