#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Decode one classic 9-symbol DJI O2 DroneID burst from HackRF int8 IQ."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

import numpy as np


FS = 15_360_000.0
FFT_SIZE = 1024
CP_LENGTHS = np.array([80, 72, 72, 72, 72, 72, 72, 72, 80])
DATA_SYMBOLS = np.array([1, 2, 4, 6, 7, 8])
CARRIER_INDICES = np.r_[212:512, 513:813]
BURST_SAMPLES = int(FFT_SIZE * 9 + CP_LENGTHS.sum())
ROOT600_USEFUL_OFFSET = int((FFT_SIZE + CP_LENGTHS[0]) +
                            (FFT_SIZE + CP_LENGTHS[1]) +
                            (FFT_SIZE + CP_LENGTHS[2]) + CP_LENGTHS[3])


def zc_carriers(root: int) -> np.ndarray:
    n = np.arange(601)
    seq = np.exp(-1j * np.pi * root * n * (n + 1) / 601.0)
    return np.delete(seq, 300)


def read_hackrf_iq(path: Path, start: int, count: int) -> np.ndarray:
    raw = np.memmap(path, dtype=np.int8, mode="r", offset=start * 2,
                    shape=(count * 2,))
    iq = raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)
    iq -= np.mean(iq)
    return iq


def cp_score(samples: np.ndarray, start: int) -> float:
    scores = []
    offset = start
    for cp_len in CP_LENGTHS:
        left = samples[offset:offset + cp_len]
        right = samples[offset + FFT_SIZE:offset + FFT_SIZE + cp_len]
        denom = np.sqrt(np.vdot(left, left).real * np.vdot(right, right).real)
        scores.append(abs(np.vdot(left, right)) / max(denom, 1e-20))
        offset += FFT_SIZE + int(cp_len)
    return float(np.mean(scores[1:]))


def choose_start(samples: np.ndarray, rough: int, radius: int = 48) -> tuple[int, float]:
    candidates = [(cp_score(samples, offset), offset)
                  for offset in range(rough - radius, rough + radius + 1)]
    return max(candidates)[1], max(candidates)[0]


def estimate_cfo(samples: np.ndarray, start: int) -> tuple[float, list[float]]:
    products = []
    scores = []
    offset = start
    for cp_len in CP_LENGTHS:
        left = samples[offset:offset + cp_len]
        right = samples[offset + FFT_SIZE:offset + FFT_SIZE + cp_len]
        product = np.vdot(left, right)
        products.append(product)
        denom = np.sqrt(np.vdot(left, left).real * np.vdot(right, right).real)
        scores.append(float(abs(product) / max(denom, 1e-20)))
        offset += FFT_SIZE + int(cp_len)
    radians_per_sample = np.angle(np.sum(products[1:])) / FFT_SIZE
    return float(radians_per_sample * FS / (2 * np.pi)), scores


def extract_symbols(samples: np.ndarray, start: int, cfo_hz: float) -> np.ndarray:
    burst = samples[start:start + BURST_SAMPLES].astype(np.complex128)
    phase = np.exp(-2j * np.pi * cfo_hz / FS * np.arange(BURST_SAMPLES))
    burst *= phase
    symbols = np.empty((9, FFT_SIZE), np.complex128)
    offset = 0
    for index, cp_len in enumerate(CP_LENGTHS):
        useful = burst[offset + cp_len:offset + cp_len + FFT_SIZE]
        symbols[index] = np.fft.fftshift(np.fft.fft(useful))
        offset += FFT_SIZE + int(cp_len)
    return symbols


def normalized_score(x: np.ndarray, y: np.ndarray) -> float:
    return float(abs(np.vdot(x, y)) /
                 np.sqrt(np.vdot(x, x).real * np.vdot(y, y).real))


def smooth_complex(values: np.ndarray, width: int = 9) -> np.ndarray:
    kernel = np.ones(width) / width
    padded = np.pad(values, (width // 2, width // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def equalize(symbols_fd: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    z600 = zc_carriers(600)
    z147 = zc_carriers(147)
    rx4 = symbols_fd[3, CARRIER_INDICES]
    rx6 = symbols_fd[5, CARRIER_INDICES]
    h4 = smooth_complex(rx4 / z600)
    h6 = smooth_complex(rx6 / z147)

    equalized = np.empty((9, 600), np.complex128)
    for symbol_index in range(9):
        # Each data symbol is at most three symbols away from one of the two
        # channel probes. This is more robust than extrapolating a noisy
        # per-carrier phase slope past the probes.
        h = h4 if symbol_index <= 4 else h6
        equalized[symbol_index] = symbols_fd[symbol_index, CARRIER_INDICES] / h

    metrics = {
        "root600_fd_score": normalized_score(rx4 / h4, z600),
        "root147_fd_score": normalized_score(rx6 / h6, z147),
        "root600_raw_fd_score": normalized_score(rx4, z600),
        "root147_raw_fd_score": normalized_score(rx6, z147),
    }
    return equalized, metrics


def gold_sequence(length: int) -> np.ndarray:
    x2_literal = [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0,
                  0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0]
    x2_init = x2_literal[::-1]
    nc = 1600
    x1 = np.zeros(nc + length + 31, np.uint8)
    x2 = np.zeros_like(x1)
    x1[0] = 1
    x2[:31] = x2_init
    for n in range(nc + length):
        x1[n + 31] = x1[n + 3] ^ x1[n]
        x2[n + 31] = x2[n + 3] ^ x2[n + 2] ^ x2[n + 1] ^ x2[n]
    return x1[nc:nc + length] ^ x2[nc:nc + length]


def make_llr(equalized: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    data = equalized[DATA_SYMBOLS].reshape(-1)
    llr = np.empty(7200, np.float32)
    llr[0::2] = -data.real
    llr[1::2] = -data.imag
    scrambler = gold_sequence(7200)
    descrambled = llr * np.where(scrambler == 0, 1.0, -1.0)
    return llr, descrambled.astype(np.float32)


def crc24a(data: bytes) -> int:
    crc = 0
    polynomial = 0x864CFB
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc = ((crc << 1) ^ polynomial) & 0xFFFFFF if crc & 0x800000 else (crc << 1) & 0xFFFFFF
    return crc


def dji_crc16(data: bytes) -> int:
    crc = 0x3692
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def parse_payload(payload: bytes) -> dict[str, object]:
    fmt = "<BBBHh16siihhhhhhQiiiiBB19sBh"
    fields = struct.unpack(fmt, payload[:91])
    names = ["packet_length", "message_type", "version", "sequence", "state",
             "serial", "longitude_raw", "latitude_raw", "height", "altitude",
             "velocity_north", "velocity_east", "velocity_up", "yaw_raw",
             "gps_time", "pilot_latitude_raw", "pilot_longitude_raw",
             "home_longitude_raw", "home_latitude_raw", "product_type",
             "uuid_length", "uuid", "null", "crc_signed"]
    result = dict(zip(names, fields))
    result["serial"] = fields[5].decode("ascii", errors="replace").rstrip("\0")
    result["uuid"] = fields[21].decode("ascii", errors="replace").rstrip("\0")
    for name in ["longitude", "latitude", "pilot_latitude", "pilot_longitude",
                 "home_longitude", "home_latitude"]:
        result[name] = result.pop(name + "_raw") / 174533.0
    result["yaw_degrees"] = result.pop("yaw_raw") / 100.0
    result["crc"] = result.pop("crc_signed") & 0xFFFF
    return result


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    _, counts = np.unique(np.frombuffer(data, dtype=np.uint8), return_counts=True)
    probabilities = counts / counts.sum()
    return float(-np.sum(probabilities * np.log2(probabilities)))


def run_decoder(llr: np.ndarray, output_dir: Path, turbo_binary: Path) -> tuple[bytes, dict[str, object]]:
    scale = 48.0 / max(float(np.percentile(abs(llr), 90)), 1e-9)
    quantized = np.clip(np.rint(llr * scale), -63, 63).astype(np.int8)
    llr_path = output_dir / "o2_descrambled_llr_int8.bin"
    quantized.tofile(llr_path)
    prefix = output_dir / "o2_turbo_input"
    best = b""
    attempts = []
    for iterations in [4, 6, 8, 12]:
        subprocess.run([str(turbo_binary), str(llr_path), str(prefix),
                        str(iterations)], check=True)
        transport = (output_dir / "o2_turbo_input_transport_176.bin").read_bytes()
        remainder = crc24a(transport)
        attempts.append({"iterations": iterations, "crc24a_remainder": f"0x{remainder:06X}"})
        best = transport
        if remainder == 0:
            break
    return best, {"llr_scale": scale, "turbo_attempts": attempts}


def decode(args: argparse.Namespace) -> dict[str, object]:
    iq_path = args.iq.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    root_index = int(round(args.root600_time * FS))
    rough_file_start = root_index - ROOT600_USEFUL_OFFSET
    read_start = max(0, rough_file_start - 256)
    samples = read_hackrf_iq(iq_path, read_start, BURST_SAMPLES + 512)
    rough_local_start = rough_file_start - read_start
    local_start, initial_cp_score = choose_start(samples, rough_local_start)
    cfo_hz, cp_scores = estimate_cfo(samples, local_start)
    symbols_fd = extract_symbols(samples, local_start, cfo_hz)
    equalized, zc_metrics = equalize(symbols_fd)
    llr, descrambled_llr = make_llr(equalized)

    np.save(output_dir / "o2_symbols_fd.npy", symbols_fd)
    np.save(output_dir / "o2_equalized.npy", equalized)
    np.save(output_dir / "o2_llr_7200.npy", llr)
    np.save(output_dir / "o2_descrambled_llr.npy", descrambled_llr)

    transport, fec_metrics = run_decoder(descrambled_llr, output_dir,
                                         args.turbo_binary.resolve())
    payload_length = min((transport[0] + 3) if transport else 0, len(transport))
    payload = transport[:payload_length]
    (output_dir / "o2_transport_176.bin").write_bytes(transport)
    (output_dir / "o2_payload.bin").write_bytes(payload)
    if len(payload) == 91:
        (output_dir / "o2_payload_91.bin").write_bytes(payload)

    crc24_remainder = crc24a(transport)
    inner_remainder = dji_crc16(payload) if payload else -1
    result: dict[str, object] = {
        "input": str(iq_path),
        "sample_rate_hz": FS,
        "root600_time_seconds": args.root600_time,
        "burst_start_sample": read_start + local_start,
        "burst_start_seconds": (read_start + local_start) / FS,
        "initial_cp_score": initial_cp_score,
        "cp_scores": cp_scores,
        "cfo_hz": cfo_hz,
        **zc_metrics,
        **fec_metrics,
        "crc24a_remainder": f"0x{crc24_remainder:06X}",
        "crc24a_ok": crc24_remainder == 0,
        "payload_length": payload_length,
        "dji_crc16_remainder": f"0x{inner_remainder & 0xFFFF:04X}",
        "dji_crc16_ok": inner_remainder == 0,
        "transport_hex": transport.hex(),
        "payload_hex": payload.hex(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
    }
    double_crc_ok = crc24_remainder == 0 and inner_remainder == 0
    is_classic_plaintext = (double_crc_ok and len(payload) == 91 and
                            payload[:3] == bytes([88, 16, 2]))
    if is_classic_plaintext:
        result["payload_classification"] = "classic_o2_plaintext"
        result["drone_id"] = parse_payload(payload)
    else:
        result["payload_classification"] = (
            "crc_valid_nonclassic_or_encrypted" if double_crc_ok
            else "crc_invalid_decode_candidate")
        result["frame_header"] = {
            "packet_length": payload[0] if len(payload) > 0 else None,
            "message_type": payload[1] if len(payload) > 1 else None,
            "byte_2": payload[2] if len(payload) > 2 else None,
            "received_dji_crc16_le": f"0x{int.from_bytes(payload[-2:], 'little'):04X}" if len(payload) >= 2 else None,
            "body_entropy_bits_per_byte": shannon_entropy(payload[2:-2]),
        }
    (output_dir / "o2_decode.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("iq", type=Path)
    parser.add_argument("--root600-time", type=float, required=True,
                        help="detected root600 useful-symbol start time in seconds")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--turbo-binary", type=Path,
                        default=Path("build/remove_turbo_soft"))
    args = parser.parse_args()
    result = decode(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
