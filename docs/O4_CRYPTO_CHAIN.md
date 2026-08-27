# O4 AA / 87 Cryptographic Chain

[English](O4_CRYPTO_CHAIN.md) | [简体中文](O4_CRYPTO_CHAIN.zh-CN.md)

## 1. Confirmed session relationship

AA carries key material and 87 carries dynamic telemetry. Bytes `6:10` of each logical packet contain a four-byte `hashcode`. An AA and its same-session 87 packets share this value.

```text
AA(hash=H) → note K
87(hash=H, nonce=N1) → AES-CTR(K, N1)
87(hash=H, nonce=N2) → AES-CTR(K, N2)
...
```

One observed note successfully decrypted at least eight 87 packets with the same hash. Sequence numbers, times, coordinates, and altitude changed coherently. The note is a session key, while each 87 packet carries its own nonce. A refreshed session requires the note paired with the new hash.

## 2. Common logical-packet header

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

## 3. AA layout

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

## 4. 87 layout and verified decryption

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

## 5. Observed plaintext fields

The verified plaintext includes version, sequence, state, a 16-byte serial-number field, raw coordinates, altitude, relative height, three axis values, yaw, millisecond time, pilot coordinates, home coordinates, product type, and a variable-length UUID.

Coordinates use signed 32-bit fixed-point radians:

```text
degrees = raw_i32 / 10_000_000 × 180 / π
```

Field layouts may vary by model and protocol version. Parsers should retain the raw plaintext and apply strict bounds checks.

## 6. A3 / 80 status

Third-party service material describes A3/80 as another key-material/dynamic-packet pair. Complete cryptographic verification in this repository currently covers AA→note→87. A3/80 offsets, IV construction, and field layouts remain separate sample-validation tasks.

## 7. Cryptanalytic boundary

Standard AES-128 exhaustive search and generic attacks against SM2-256 both provide roughly 128-bit security. Productive implementation checks include:

- low-entropy note derivation or time-based seeds;
- repeated AA C1 points;
- nonce collisions under the same note;
- business public keys, key IDs, or offline decryptors in firmware;
- curve-point validation and side-channel behavior in explicitly authorized implementations.

The public key may be present in aircraft firmware, configuration storage, or a secure module. It can confirm the key hierarchy and locate the encryption path; AA decryption requires the matching private key. Private-key deployment is more likely in a server HSM or an offline-capable receiver.
