# DJI DroneID research status — 30 October 2026

[English](STATUS.md) | [简体中文](STATUS.zh-CN.md) | [Evidence ledger](FACTS.md) | [Home](README.md)

This is a dated status snapshot, **not** a claim that the long-term SM2 recipient private key has been extracted. It combines repository work, public discussions, and the owner's own report about ongoing private hardware research. **Source tiers are explicit**: `REPO-REPRODUCED` (repo code/captures), `PUBLIC-SPEC` (linked reference implementation), `PUBLIC-REPORT` (attributed GitHub claim), `OWNER-REPORTED / PRIVATE` (communicated by the owner, not publicly reproducible), and `OPEN`. Do not convert a screenshot or personal message into independent proof.

## Executive status

| Component | Status as of 2026-10-30 | Evidence / boundary |
|---|---|---|
| Classic v2/O2 DroneID PHY, turbo/FEC, CRC | **REPO-REPRODUCED** | [O2 decoder](src/o2_droneid_decode.py), [Turbo adapter](tools/remove_turbo_soft.c); historic **9-symbol** baseline |
| O4 CRYP / INFP-10 / INFP-11 packet & crypto chain | **PUBLIC-SPEC + local packet observations** | [EdwardBlair specification](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/README.md), [reference code](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/droneid.py), [local packet tool](src/o4_packet_tool.py) |
| V3/newer DroneID RF/PHY | **PUBLIC-SPEC; not yet integrated into local classic scanner** | [RF_PHY.md](https://github.com/EdwardBlair/dji-droneid-spec/blob/55bb88676dbc75913f074d7816ed5f7a3ab92454/RF_PHY.md) specifies **8 OFDM symbols**, **173-byte payload** plus CRC24A, 15.36 MS/s; do not identify as the local O2 nine-symbol PHY |
| Full O4 decode using **real AeroScope dongle** | **PUBLIC-REPORT; OWNER-REPORTED EXPERIENCE** | [King-Of-Knights dongle console demonstration](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456); [owner's public report of offline decoding based on that research](https://github.com/proto17/dji_droneid/issues/60#issuecomment-6078335828). Independent USB command protocol and reproducible source remain non-public |
| Host ↔ dongle communication emulation / authentication | **OWNER-REPORTED / PRIVATE** | The owner reports that the host-side emulation/pass-through work has been completed in private research discussions; do **not** equate that with emulating the cryptographic hardware, dumping firmware or extracting its key |
| Physical dongle X-ray inspection | **OWNER-REPORTED / PRIVATE** | The owner reports completion of X-ray inspection/analysis; a hypothesized chip/COB or bonding-wire area (marked **#4** in discussed images) is **not** a confirmed chip identity or private-key storage location. Original images and repeatable measurements have not been published in this repo |
| Session-key partial predictability / reduced effective entropy (route 2) | **OWNER-REPORTED / PRIVATE; owner reports scalable applicability** | Owner update 2026-10-30: some `K` bytes are reportedly fixed/derivable and residual randomness limited. No public independent per-byte analysis, firmware coverage, controlled captures or code; this is not extraction of the SM2 private scalar |
| Chip opening / decapsulation / extraction | **OPEN / NEXT PHASE** | Chip analysis was described as the next step; **no completed invasive extraction** or public die analysis is established by the material reviewed |
| Recovering real recipient SM2 private scalar `d` | **OPEN** | Neither this repo nor [the public spec (dummy test keys only)](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454/keys) publishes the real scalar. A dongle that unwraps CRYP does not expose `d` |
| Public, reproducible, **dongle-free** decryption of a captured real O4 session | **OPEN** | Synthetic SM2/AES tests establish interoperability, not recovery of the private key or a real captured session |
| Unencrypted startup DroneID in O4 | **DISPUTED / NOT REPRODUCED** | [Issue #3: a Mavic 4 Pro startup plaintext report](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3#issuecomment-6459214434); [EdwardBlair requests exact firmware](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3#issuecomment-6459273901). Do not generalize to all O4 |

## Session-key predictability research update (30 October 2026; owner-reported)

The owner now identifies **route 2, rather than invasive extraction of the long-term SM2 private scalar, as the privately validated potentially scalable approach**. The claim is that, in certain investigated implementations, the **aircraft DroneID session key `K`** includes fixed/derivable bytes and bytes with limited effective randomness. A constrained candidate search could recover `K`, subject to cross-checks against `key_id = SHA-256(K)[0:4]` and multiple same-session INFP plaintexts. This describes a potential weakness in key generation, **not** solving the SM2 discrete logarithm problem or breaking AES-128 itself.

**Evidence tier: `OWNER-REPORTED / PRIVATE`.** The owner reports private confirmation and practical generalizability, but this repository does **not** yet contain independently checkable sanitized captures, byte-level entropy results, device/firmware coverage, recovery code, or cross-device statistics. **The public protocol's freshly random AES-128 key remains the baseline model**; any implementation-specific deviations require separate validation. No claim is made that this applies to every O4 aircraft or to most manufacturers.

The **aircraft DroneID session key `K`** and the **AeroScope host↔dongle transport-session key** are distinct. A 4-byte `key_id` alone is not sufficient proof due to possible collisions; candidate validation needs multiple same-session records and structural plaintext checks. Publicly reproducible, completely dongle-free decryption remains **OPEN** until supporting material is published.

## Attribution: King-Of-Knights and private conversations

The repository owner **identifies the individual in previously shared private chat screenshots as the GitHub account [King-Of-Knights](https://github.com/King-Of-Knights)**. This establishes the owner's attribution of the *chat correspondent*, **not** that the owner and that GitHub account are the same individual, or that any unposted screenshot is independently authenticated.

- **King-Of-Knights (public):** posted [console output](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1#issuecomment-5957785456) indicating that an authentic AeroScope module accepted CRYP, returned a 16-byte AES session key, and was then used to obtain decrypted INFP telemetry. This is a **hardware-assisted offline decoder**, not a published 256-bit SM2 private key.
- **Owner-side collaboration (private):** owner reports successful host-side dongle communication emulation and X-ray research, with invasive chip investigation still pending. The available context does not uniquely establish which collaborator physically performed each operation. Accordingly, record these as *owner-reported collaborative progress*, not as separately verified experiments attributed to a specific person.
- **Private-chat “key” value:** a 128-hex-character (~64-byte) value discussed as a possible “key” has the length/shape of an **SM2 public point** `Qx || Qy` (32+32 bytes), **not evidence** of the **32-byte SM2 private scalar** `d`. Even passing the curve equation cannot establish that it belongs to the actual AeroScope recipient. Do not publish the private chat, hexadecimal value, chip imagery, or inferred ownership without permission and provenance.

The [2024 Edgesource teardown](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf) documents earlier physical disassembly and a separate host–dongle transport session. Its photographs do not establish which 2026 researcher performed which teardown; it does **not** establish that the device uses a TEE.

## Current cryptographic boundary

```text
Aircraft:
  fresh 16-byte AES key K
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

## Latest RF/PHY evidence and limitation of this repository's scanner

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
- For a new confirmed real-session test: retain one original CRYP, at least two matching INFPs, CRC/FEC validity, authorized 16-byte **session key** (not recipient private key), model/firmware and privacy-safe test ground truth. Never commit authentic private keys, hardware credentials, unredacted serial numbers, operator/home locations, private chat screenshots, or raw X-ray media without deliberate disclosure approval.
- The next hardware milestone is **independently documented chip identity / die / memory findings** after authorized analysis; X-ray evidence alone cannot localize the SM2 private scalar. More narrowly, a reproducible *host-side* dongle interface would verify hardware-assisted offline decoding without requiring the key to leave the dongle.

## Primary sources

- [Own Issue #1: crypto and dongle](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/1)
- [Own Issue #2: frequencies](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/2)
- [Own Issue #3: disputed startup plaintext](https://github.com/luyii-code-1/dji-ocusync-droneid-research/issues/3)
- [EdwardBlair protocol spec (22 Oct 2026)](https://github.com/EdwardBlair/dji-droneid-spec/tree/55bb88676dbc75913f074d7816ed5f7a3ab92454)
- [proto17 Issue #60: receiver and hop research](https://github.com/proto17/dji_droneid/issues/60)
- [Edgesource 2024 hardware paper](https://www.aerial-defence.com/wp-content/uploads/2024/03/Security-Risks-of-the-Aeroscope-Upgrade-Module-Whitepaper-March-2024.pdf)
