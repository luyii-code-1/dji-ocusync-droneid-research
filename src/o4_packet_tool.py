#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Inspect DJI O4 AA packets and decrypt 87 packets with an API note key.

The observed 87 format uses AES-128-CTR.  The 16-byte key is the hexadecimal
``note`` returned after the paired AA packet is accepted.  The IV is the
8-byte value at packet offsets 10..17 followed by eight zero bytes.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SM2_P = int("FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF", 16)
SM2_A = int("FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC", 16)
SM2_B = int("28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93", 16)

PRODUCT_NAMES = {112: "Mini 5 Pro"}


def dji_crc16(data: bytes) -> int:
    crc = 0x3692
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def packet_bytes(value: str) -> bytes:
    candidate = Path(value)
    if candidate.is_file():
        value = candidate.read_text(encoding="utf-8").strip()
    return bytes.fromhex("".join(value.split()))


def radians_i32_to_degrees(value: int) -> float:
    return value / 10_000_000.0 * 180.0 / math.pi


def sm2_point_valid(raw_xy: bytes) -> bool:
    if len(raw_xy) != 64:
        return False
    x = int.from_bytes(raw_xy[:32], "big")
    y = int.from_bytes(raw_xy[32:], "big")
    return (
        x < SM2_P
        and y < SM2_P
        and (y * y - (x * x * x + SM2_A * x + SM2_B)) % SM2_P == 0
    )


def common_header(packet: bytes) -> dict[str, object]:
    if len(packet) < 12:
        raise ValueError("packet is too short")
    logical_length = packet[0] + 3
    return {
        "packet_length": len(packet),
        "declared_length": logical_length,
        "length_ok": len(packet) == logical_length,
        "message_type": packet[1],
        "marker": packet[2:6].decode("ascii", errors="replace"),
        "hashcode": packet[6:10].hex(),
        "dji_crc16_ok": dji_crc16(packet) == 0,
        "received_crc16_le": f"0x{int.from_bytes(packet[-2:], 'little'):04X}",
    }


def inspect_aa(packet: bytes) -> dict[str, object]:
    result = common_header(packet)
    if packet[:2] != b"\xaa\x13" or packet[2:6] != b"CRYP":
        raise ValueError("not an AA/CRYP packet")
    c1 = packet[10:74]
    result.update(
        {
            "classification": "AA key-material packet",
            "sm2_c1_xy": c1.hex(),
            "sm2_c1_x": c1[:32].hex(),
            "sm2_c1_y": c1[32:].hex(),
            "sm2_c1_valid": sm2_point_valid(c1),
            "sm2_c3_candidate": packet[74:106].hex(),
            "sm2_c2_candidate": packet[106:122].hex(),
            "sm2_c2_length": len(packet[106:122]),
            "dynamic_8": packet[122:130].hex(),
            "tail_32_length_le": int.from_bytes(packet[130:132], "little"),
            "tail_32": packet[132:164].hex(),
        }
    )
    return result


def openssl_aes_128_ctr(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    if len(key) != 16 or len(iv) != 16:
        raise ValueError("AES-128 key and IV must each be 16 bytes")
    process = subprocess.run(
        [
            "openssl",
            "enc",
            "-d",
            "-aes-128-ctr",
            "-K",
            key.hex(),
            "-iv",
            iv.hex(),
        ],
        input=ciphertext,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.decode("utf-8", errors="replace").strip())
    return process.stdout


def decrypt_87(packet: bytes, note_hex: str) -> dict[str, object]:
    result = common_header(packet)
    if packet[:2] != b"\x87\x10" or packet[2:6] != b"INFP":
        raise ValueError("not an 87/INFP packet")
    key = bytes.fromhex(note_hex)
    if len(key) != 16:
        raise ValueError("note must be exactly 16 bytes (32 hexadecimal characters)")
    nonce = packet[10:18]
    encrypted_length = int.from_bytes(packet[18:20], "little")
    ciphertext = packet[20 : 20 + encrypted_length]
    if len(ciphertext) != encrypted_length:
        raise ValueError("truncated encrypted body")
    plaintext = openssl_aes_128_ctr(ciphertext, key, nonce + bytes(8))
    if len(plaintext) < 68:
        raise ValueError("decrypted body is too short")

    def i16(offset: int) -> int:
        return struct.unpack_from("<h", plaintext, offset)[0]

    def i32(offset: int) -> int:
        return struct.unpack_from("<i", plaintext, offset)[0]

    gps_time_ms = struct.unpack_from("<Q", plaintext, 42)[0]
    uuid_length = plaintext[67]
    uuid_raw = plaintext[68 : 68 + uuid_length]
    product_type = plaintext[66]
    longitude_raw = i32(22)
    latitude_raw = i32(26)
    pilot_latitude_raw = i32(50)
    pilot_longitude_raw = i32(54)
    home_longitude_raw = i32(58)
    home_latitude_raw = i32(62)

    result.update(
        {
            "classification": "87 decrypted telemetry",
            "cipher": "AES-128-CTR",
            "nonce_8": nonce.hex(),
            "iv_16": (nonce + bytes(8)).hex(),
            "encrypted_length": encrypted_length,
            "plaintext_hex": plaintext.hex(),
            "version": plaintext[1],
            "seq_num": struct.unpack_from("<H", plaintext, 2)[0],
            "state": f"0x{struct.unpack_from('<H', plaintext, 4)[0]:04X}",
            "sn": plaintext[6:22].rstrip(b"\x00").decode("ascii", errors="replace"),
            "longitude_raw": longitude_raw,
            "latitude_raw": latitude_raw,
            "lon": radians_i32_to_degrees(longitude_raw),
            "lat": radians_i32_to_degrees(latitude_raw),
            "alt": i16(30),
            "height": i16(32) / 10.0,
            "x_raw": i16(34),
            "y_raw": i16(36),
            "z_raw": i16(38),
            "yaw": i16(40) / 100.0,
            "gps_time_ms": gps_time_ms,
            "gps_time": datetime.fromtimestamp(
                gps_time_ms / 1000.0, timezone.utc
            ).isoformat(timespec="milliseconds"),
            "pilot_lat": radians_i32_to_degrees(pilot_latitude_raw),
            "pilot_lon": radians_i32_to_degrees(pilot_longitude_raw),
            "home_lon": radians_i32_to_degrees(home_longitude_raw),
            "home_lat": radians_i32_to_degrees(home_latitude_raw),
            "type": product_type,
            "model": PRODUCT_NAMES.get(product_type, f"DJI type {product_type}"),
            "uuid_length": uuid_length,
            "uuid": uuid_raw.decode("ascii", errors="replace"),
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", help="packet Hex or a text file containing Hex")
    parser.add_argument("--note", help="16-byte hexadecimal key returned by AA API call")
    args = parser.parse_args()
    packet = packet_bytes(args.packet)
    if packet.startswith(b"\xaa\x13CRYP"):
        result = inspect_aa(packet)
    elif packet.startswith(b"\x87\x10INFP"):
        if not args.note:
            parser.error("--note is required for an 87 packet")
        result = decrypt_87(packet, args.note)
    else:
        raise SystemExit("unsupported packet header")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
