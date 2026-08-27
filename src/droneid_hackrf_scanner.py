#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real-time DJI DroneID scanner for HackRF One.

The scanner cycles through known OcuSync raster frequencies, detects the
classic 9-symbol root600/root147 shell, and runs the verified O2/O3 payload
pipeline. CRC-valid classic frames are printed as telemetry; CRC-valid newer
frames are printed as encrypted payload HEX and fingerprints.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import json
import math
import queue
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
from scipy.signal import fftconvolve, find_peaks

import o2_droneid_decode as o2


FREQUENCIES_2G = [
    2_444_500_000,
    2_429_500_000,
    2_414_500_000,
    2_459_500_000,
    2_399_500_000,
]
FREQUENCIES_5G = [5_756_500_000, 5_776_500_000, 5_796_500_000]
PRODUCT_NAMES = {63: "DJI Mini 2"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def frequency_label(freq_hz: int) -> str:
    return f"{freq_hz / 1e6:.4f} MHz"


def parse_frequency(value: str) -> int:
    text = value.strip().lower().replace("mhz", "").replace("_", "")
    number = float(text)
    return int(round(number * 1e6 if number < 100_000 else number))


def make_time_reference(root: int) -> np.ndarray:
    fd = np.zeros(o2.FFT_SIZE, np.complex128)
    fd[o2.CARRIER_INDICES] = o2.zc_carriers(root)
    return np.fft.ifft(np.fft.ifftshift(fd))


ROOT600_REFERENCE = make_time_reference(600)
ROOT147_REFERENCE = make_time_reference(147)
ROOT600_ENERGY = float(np.vdot(ROOT600_REFERENCE, ROOT600_REFERENCE).real)
ROOT147_ENERGY = float(np.vdot(ROOT147_REFERENCE, ROOT147_REFERENCE).real)


def iq_window(raw: np.ndarray, start: int, count: int) -> np.ndarray:
    values = raw[start * 2:(start + count) * 2]
    iq = values[0::2].astype(np.float32) + 1j * values[1::2].astype(np.float32)
    iq -= np.mean(iq)
    return iq


def reference_score(raw: np.ndarray, start: int, reference: np.ndarray,
                    reference_energy: float) -> float:
    if start < 0 or start + len(reference) > raw.size // 2:
        return 0.0
    samples = iq_window(raw, start, len(reference))
    energy = float(np.vdot(samples, samples).real)
    if energy <= 0:
        return 0.0
    return float(abs(np.vdot(reference, samples)) /
                 math.sqrt(reference_energy * energy))


def average_power_dbfs(raw: np.ndarray) -> float:
    if raw.size < 2:
        return float("-inf")
    values = raw.astype(np.float32)
    power = float(np.mean(values * values) * 2.0 / (128.0 * 128.0))
    return 10.0 * math.log10(max(power, 1e-20))


@dataclass
class CaptureBatch:
    frequency_hz: int
    data: bytearray
    started_wall_ns: int
    dwell_seconds: float
    source: str = "hackrf"


class HackRFTransfer(ctypes.Structure):
    _fields_ = [
        ("device", ctypes.c_void_p),
        ("buffer", ctypes.POINTER(ctypes.c_uint8)),
        ("buffer_length", ctypes.c_int),
        ("valid_length", ctypes.c_int),
        ("rx_ctx", ctypes.c_void_p),
        ("tx_ctx", ctypes.c_void_p),
    ]


RX_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(HackRFTransfer))


class HackRFReceiver:
    def __init__(self, lib_path: Path, sample_rate: float, lna_gain: int,
                 vga_gain: int, amp: bool, serial_number: str | None = None):
        self.lib = ctypes.CDLL(str(lib_path))
        self.sample_rate = sample_rate
        self.serial_number = serial_number
        self.device = ctypes.c_void_p()
        self._lock = threading.Lock()
        self._buffer = bytearray()
        self._collecting = False
        self._callback = RX_CALLBACK(self._receive_callback)
        self._configure_signatures()

        self._check(self.lib.hackrf_init(), "hackrf_init")
        try:
            if serial_number:
                status = self.lib.hackrf_open_by_serial(
                    serial_number.encode("ascii"), ctypes.byref(self.device))
            else:
                status = self.lib.hackrf_open(ctypes.byref(self.device))
            self._check(status, "hackrf_open")
            self._check(self.lib.hackrf_set_sample_rate(self.device, sample_rate),
                        "hackrf_set_sample_rate")
            self._check(self.lib.hackrf_set_baseband_filter_bandwidth(
                self.device, 10_000_000), "hackrf_set_baseband_filter_bandwidth")
            self._check(self.lib.hackrf_set_lna_gain(self.device, lna_gain),
                        "hackrf_set_lna_gain")
            self._check(self.lib.hackrf_set_vga_gain(self.device, vga_gain),
                        "hackrf_set_vga_gain")
            self._check(self.lib.hackrf_set_amp_enable(self.device, int(amp)),
                        "hackrf_set_amp_enable")
            self._check(self.lib.hackrf_set_antenna_enable(self.device, 0),
                        "hackrf_set_antenna_enable")
        except Exception:
            if self.device:
                self.lib.hackrf_close(self.device)
            self.lib.hackrf_exit()
            raise

    def _configure_signatures(self) -> None:
        self.lib.hackrf_error_name.argtypes = [ctypes.c_int]
        self.lib.hackrf_error_name.restype = ctypes.c_char_p
        self.lib.hackrf_open.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        self.lib.hackrf_open.restype = ctypes.c_int
        self.lib.hackrf_open_by_serial.argtypes = [
            ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
        self.lib.hackrf_open_by_serial.restype = ctypes.c_int
        self.lib.hackrf_close.argtypes = [ctypes.c_void_p]
        self.lib.hackrf_close.restype = ctypes.c_int
        self.lib.hackrf_set_sample_rate.argtypes = [ctypes.c_void_p, ctypes.c_double]
        self.lib.hackrf_set_sample_rate.restype = ctypes.c_int
        self.lib.hackrf_set_baseband_filter_bandwidth.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32]
        self.lib.hackrf_set_baseband_filter_bandwidth.restype = ctypes.c_int
        self.lib.hackrf_set_lna_gain.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.lib.hackrf_set_lna_gain.restype = ctypes.c_int
        self.lib.hackrf_set_vga_gain.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.lib.hackrf_set_vga_gain.restype = ctypes.c_int
        self.lib.hackrf_set_amp_enable.argtypes = [ctypes.c_void_p, ctypes.c_uint8]
        self.lib.hackrf_set_amp_enable.restype = ctypes.c_int
        self.lib.hackrf_set_antenna_enable.argtypes = [ctypes.c_void_p, ctypes.c_uint8]
        self.lib.hackrf_set_antenna_enable.restype = ctypes.c_int
        self.lib.hackrf_set_freq.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        self.lib.hackrf_set_freq.restype = ctypes.c_int
        self.lib.hackrf_start_rx.argtypes = [ctypes.c_void_p, RX_CALLBACK, ctypes.c_void_p]
        self.lib.hackrf_start_rx.restype = ctypes.c_int
        self.lib.hackrf_stop_rx.argtypes = [ctypes.c_void_p]
        self.lib.hackrf_stop_rx.restype = ctypes.c_int

    def _check(self, status: int, operation: str) -> None:
        if status == 0:
            return
        name = self.lib.hackrf_error_name(status)
        detail = name.decode("utf-8", errors="replace") if name else str(status)
        raise RuntimeError(f"{operation} failed: {detail} ({status})")

    def _receive_callback(self, transfer_pointer: ctypes.POINTER(HackRFTransfer)) -> int:
        transfer = transfer_pointer.contents
        if transfer.valid_length <= 0:
            return 0
        with self._lock:
            if self._collecting:
                self._buffer.extend(ctypes.string_at(transfer.buffer,
                                                     transfer.valid_length))
        return 0

    def start(self, initial_frequency_hz: int) -> None:
        self._check(self.lib.hackrf_set_freq(self.device, initial_frequency_hz),
                    "hackrf_set_freq")
        self._check(self.lib.hackrf_start_rx(self.device, self._callback, None),
                    "hackrf_start_rx")

    def capture_dwell(self, frequency_hz: int, dwell_seconds: float,
                      settle_seconds: float) -> CaptureBatch:
        with self._lock:
            self._collecting = False
            self._buffer = bytearray()
        self._check(self.lib.hackrf_set_freq(self.device, frequency_hz),
                    "hackrf_set_freq")
        time.sleep(settle_seconds)
        started_wall_ns = time.time_ns()
        with self._lock:
            self._buffer = bytearray()
            self._collecting = True
        time.sleep(dwell_seconds)
        with self._lock:
            self._collecting = False
            data = self._buffer
            self._buffer = bytearray()
        return CaptureBatch(frequency_hz, data, started_wall_ns, dwell_seconds)

    def close(self) -> None:
        with self._lock:
            self._collecting = False
        if self.device:
            self.lib.hackrf_stop_rx(self.device)
            self.lib.hackrf_close(self.device)
            self.device = ctypes.c_void_p()
        self.lib.hackrf_exit()


class DroneIDDetector:
    def __init__(self, output_root: Path, turbo_binary: Path,
                 root600_threshold: float, root147_threshold: float,
                 save_candidates: bool = True):
        self.output_root = output_root.resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.turbo_binary = turbo_binary.resolve()
        self.root600_threshold = root600_threshold
        self.root147_threshold = root147_threshold
        self.save_candidates = save_candidates
        self.event_log = self.output_root / "detections.jsonl"
        self.batch_count = 0
        self.detection_count = 0
        self.crc_valid_count = 0
        self._event_lock = threading.Lock()

    def _root600_candidates(self, raw: np.ndarray) -> list[tuple[int, float]]:
        total = raw.size // 2
        chunk_size = 4_000_000
        candidates: list[tuple[int, float]] = []
        for output_start in range(0, total, chunk_size):
            output_end = min(total - o2.FFT_SIZE + 1,
                             output_start + chunk_size)
            if output_end <= output_start:
                continue
            input_start = max(0, output_start - (o2.FFT_SIZE - 1))
            input_end = min(total, output_end + o2.FFT_SIZE - 1)
            samples = iq_window(raw, input_start, input_end - input_start)
            correlation = fftconvolve(
                samples, np.conj(ROOT600_REFERENCE[::-1]), mode="valid")
            cumulative = np.empty(len(samples) + 1, np.float64)
            cumulative[0] = 0.0
            np.cumsum(samples.real * samples.real + samples.imag * samples.imag,
                      out=cumulative[1:])
            energy = cumulative[o2.FFT_SIZE:] - cumulative[:-o2.FFT_SIZE]
            scores = np.abs(correlation) / np.sqrt(
                np.maximum(energy * ROOT600_ENERGY, 1e-20))
            local_peaks, properties = find_peaks(
                scores, height=self.root600_threshold, distance=2_000)
            for local_index, score in zip(local_peaks, properties["peak_heights"]):
                global_index = input_start + int(local_index)
                if output_start <= global_index < output_end:
                    candidates.append((global_index, float(score)))

        candidates.sort(key=lambda item: item[1], reverse=True)
        kept: list[tuple[int, float]] = []
        for index, score in candidates:
            if all(abs(index - other_index) > 5_000 for other_index, _ in kept):
                kept.append((index, score))
        return sorted(kept)

    def _candidate_name(self, batch: CaptureBatch, root_index: int) -> str:
        event_ns = batch.started_wall_ns + int(root_index / o2.FS * 1e9)
        stamp = datetime.fromtimestamp(event_ns / 1e9, timezone.utc).strftime(
            "%Y%m%dT%H%M%S.%fZ")
        return f"{stamp}_{batch.frequency_hz}_s{root_index}"

    def _decode_candidate(self, batch: CaptureBatch, raw: np.ndarray,
                          root_index: int, root600_score: float,
                          root147_score: float) -> dict[str, Any]:
        rough_start = root_index - o2.ROOT600_USEFUL_OFFSET
        extraction_start = rough_start - 256
        extraction_end = rough_start + o2.BURST_SAMPLES + 256
        if extraction_start < 0 or extraction_end > raw.size // 2:
            return {
                "status": "clipped",
                "reason": "candidate too close to dwell boundary",
            }

        event_name = self._candidate_name(batch, root_index)
        event_dir = self.output_root / event_name
        event_dir.mkdir(parents=True, exist_ok=True)
        candidate_iq = event_dir / "candidate.iq"
        candidate_bytes = raw[extraction_start * 2:extraction_end * 2].tobytes()
        candidate_iq.write_bytes(candidate_bytes)
        local_root_time = (root_index - extraction_start) / o2.FS
        decode_args = SimpleNamespace(
            iq=candidate_iq,
            root600_time=local_root_time,
            output=event_dir,
            turbo_binary=self.turbo_binary,
        )
        result = o2.decode(decode_args)
        event_wall_ns = batch.started_wall_ns + int(root_index / o2.FS * 1e9)
        result.update({
            "event_directory": str(event_dir),
            "event_time_utc": datetime.fromtimestamp(
                event_wall_ns / 1e9, timezone.utc).isoformat(timespec="milliseconds"),
            "frequency_hz": batch.frequency_hz,
            "frequency_mhz": batch.frequency_hz / 1e6,
            "root600_time_score": root600_score,
            "root147_time_score": root147_score,
            "dwell_source": batch.source,
            "dwell_average_power_dbfs": average_power_dbfs(raw),
        })
        (event_dir / "detection.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        return result

    def _print_result(self, result: dict[str, Any]) -> None:
        classification = result.get("payload_classification", "unknown")
        double_crc_ok = bool(result.get("crc24a_ok") and result.get("dji_crc16_ok"))
        crc24 = "OK" if result.get("crc24a_ok") else "FAIL"
        crc16 = "OK" if result.get("dji_crc16_ok") else "FAIL"
        print("\n" + "=" * 78)
        print(f"DRONEID DETECTED  {result['event_time_utc']}  "
              f"{frequency_label(result['frequency_hz'])}")
        print(f"ZC600={result['root600_time_score']:.3f}  "
              f"ZC147={result['root147_time_score']:.3f}  "
              f"CFO={result.get('cfo_hz', 0):+.1f} Hz  "
              f"CRC24A={crc24}  DJI-CRC16={crc16}")
        if classification == "classic_o2_plaintext" and "drone_id" in result:
            drone = result["drone_id"]
            product = int(drone["product_type"])
            print(f"TYPE: O2/O3 PLAINTEXT  MODEL: "
                  f"{PRODUCT_NAMES.get(product, f'DJI type {product}')}")
            print(f"SERIAL: {drone['serial']}  UUID: {drone['uuid']}  "
                  f"SEQ: {drone['sequence']}")
            print(f"DRONE: lat={drone['latitude']:.7f} "
                  f"lon={drone['longitude']:.7f} height={drone['height']} "
                  f"alt={drone['altitude']}")
            print(f"VELOCITY: N={drone['velocity_north']} "
                  f"E={drone['velocity_east']} U={drone['velocity_up']} "
                  f"yaw={drone['yaw_degrees']:.2f} deg")
            print(f"PILOT: lat={drone['pilot_latitude']:.7f} "
                  f"lon={drone['pilot_longitude']:.7f}  "
                  f"HOME: lat={drone['home_latitude']:.7f} "
                  f"lon={drone['home_longitude']:.7f}")
        elif double_crc_ok:
            header = result.get("frame_header", {})
            print("TYPE: ENCRYPTED / NEW PAYLOAD")
            print(f"LENGTH: {result.get('payload_length')} bytes  "
                  f"STABLE/CLEAR PREFIX: {result.get('payload_hex', '')[:20]}")
            print(f"PAYLOAD SHA256: {result.get('payload_sha256', '')}")
            if header:
                print(f"HEADER: length={header.get('packet_length')} "
                      f"type=0x{int(header.get('message_type', 0)):02X} "
                      f"byte2=0x{int(header.get('byte_2', 0)):02X}")
        else:
            print("TYPE: PAIRED-ZC PHY CANDIDATE; PAYLOAD CRC INVALID")
            print("The burst is saved for later recovery and is not interpreted.")
        print(f"PAYLOAD HEX: {result.get('payload_hex', '')}")
        print("=" * 78, flush=True)

    def _log_event(self, result: dict[str, Any]) -> None:
        with self._event_lock:
            with self.event_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")

    def process_batch(self, batch: CaptureBatch) -> list[dict[str, Any]]:
        self.batch_count += 1
        raw = np.frombuffer(batch.data, dtype=np.int8)
        if raw.size % 2:
            raw = raw[:-1]
        sample_count = raw.size // 2
        if sample_count < o2.BURST_SAMPLES:
            return []
        outputs = []
        for root_index, root600_score in self._root600_candidates(raw):
            root147_index = root_index + 2 * (o2.FFT_SIZE + 72)
            root147_score = reference_score(
                raw, root147_index, ROOT147_REFERENCE, ROOT147_ENERGY)
            if root147_score < self.root147_threshold:
                continue
            self.detection_count += 1
            try:
                result = self._decode_candidate(
                    batch, raw, root_index, root600_score, root147_score)
            except Exception as error:
                result = {
                    "status": "decode_error",
                    "error": repr(error),
                    "frequency_hz": batch.frequency_hz,
                    "root600_time_score": root600_score,
                    "root147_time_score": root147_score,
                    "root_index": root_index,
                    "time_utc": utc_now_iso(),
                }
                print(f"\nDecode error at {frequency_label(batch.frequency_hz)}: {error}",
                      file=sys.stderr, flush=True)
            if result.get("crc24a_ok") and result.get("dji_crc16_ok"):
                self.crc_valid_count += 1
            self._log_event(result)
            if "event_time_utc" in result:
                self._print_result(result)
            outputs.append(result)
        return outputs


class DetectorWorker(threading.Thread):
    def __init__(self, detector: DroneIDDetector, work_queue: queue.Queue[Any]):
        super().__init__(name="droneid-detector", daemon=True)
        self.detector = detector
        self.work_queue = work_queue

    def run(self) -> None:
        while True:
            batch = self.work_queue.get()
            try:
                if batch is None:
                    return
                self.detector.process_batch(batch)
            finally:
                self.work_queue.task_done()


def select_frequencies(args: argparse.Namespace) -> list[int]:
    if args.freqs:
        frequencies = [parse_frequency(item) for item in args.freqs.split(",")]
    elif args.band == "2g":
        frequencies = FREQUENCIES_2G
    elif args.band == "5g":
        frequencies = FREQUENCIES_5G
    else:
        frequencies = FREQUENCIES_2G + FREQUENCIES_5G
    if not frequencies:
        raise ValueError("frequency list is empty")
    return frequencies


def run_replay(args: argparse.Namespace, detector: DroneIDDetector) -> int:
    if args.replay_freq is None:
        raise ValueError("--replay-freq is required with --replay")
    path = args.replay.resolve()
    print(f"Replaying {path} at {frequency_label(args.replay_freq)}")
    batch = CaptureBatch(
        args.replay_freq,
        bytearray(path.read_bytes()),
        time.time_ns(),
        path.stat().st_size / 2 / o2.FS,
        source=str(path),
    )
    results = detector.process_batch(batch)
    print(f"Replay complete: {len(results)} paired-ZC detections, "
          f"{sum(bool(x.get('crc24a_ok') and x.get('dji_crc16_ok')) for x in results)} "
          "double-CRC-valid frames")
    return 0 if results else 1


def run_live(args: argparse.Namespace, detector: DroneIDDetector) -> int:
    frequencies = select_frequencies(args)
    work_queue: queue.Queue[Any] = queue.Queue(maxsize=args.queue_depth)
    worker = DetectorWorker(detector, work_queue)
    worker.start()
    receiver = HackRFReceiver(
        args.libhackrf.resolve(), o2.FS, args.lna, args.vga, args.amp,
        args.serial)
    stop_event = threading.Event()

    def request_stop(_signum: int, _frame: Any) -> None:
        stop_event.set()

    old_sigint = signal.signal(signal.SIGINT, request_stop)
    old_sigterm = signal.signal(signal.SIGTERM, request_stop)
    try:
        receiver.start(frequencies[0])
        print("HackRF DroneID scanner started (RX only)")
        print(f"Fs={o2.FS / 1e6:.2f} MS/s LNA={args.lna} VGA={args.vga} "
              f"AMP={'ON' if args.amp else 'OFF'} dwell={args.dwell:.3f}s")
        print("Frequencies: " + ", ".join(frequency_label(x) for x in frequencies))
        print(f"Results: {detector.output_root}")
        cycle = 0
        while not stop_event.is_set() and (args.cycles == 0 or cycle < args.cycles):
            cycle += 1
            for index, frequency_hz in enumerate(frequencies, 1):
                if stop_event.is_set():
                    break
                batch = receiver.capture_dwell(
                    frequency_hz, args.dwell, args.settle)
                samples = len(batch.data) // 2
                print(f"\rCycle {cycle} [{index}/{len(frequencies)}] "
                      f"{frequency_label(frequency_hz)} "
                      f"{samples / o2.FS:.3f}s captured | "
                      f"queue={work_queue.qsize()} detections={detector.detection_count} "
                      f"valid={detector.crc_valid_count}   ",
                      end="", flush=True)
                try:
                    work_queue.put(batch, timeout=0.1)
                except queue.Full:
                    print("\nDetector queue full; dropping one dwell", file=sys.stderr)
        print("\nStopping receiver; finishing queued analysis...")
    finally:
        receiver.close()
        work_queue.join()
        work_queue.put(None)
        work_queue.join()
        worker.join(timeout=5)
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)
    print(f"Stopped. paired-ZC={detector.detection_count}, "
          f"double-CRC-valid={detector.crc_valid_count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Real-time HackRF DJI DroneID scanner and O2/O3 decoder")
    parser.add_argument("--band", choices=["2g", "5g", "both"], default="2g")
    parser.add_argument("--freqs", help="comma-separated Hz or MHz override")
    parser.add_argument("--dwell", type=float, default=0.80,
                        help="seconds captured at each frequency (default: 0.80)")
    parser.add_argument("--settle", type=float, default=0.030,
                        help="discarded tuner settling time (default: 0.030)")
    parser.add_argument("--cycles", type=int, default=0,
                        help="number of full scans; 0 runs until Ctrl-C")
    parser.add_argument("--lna", type=int, default=16)
    parser.add_argument("--vga", type=int, default=20)
    parser.add_argument("--amp", action="store_true",
                        help="enable RF amp; default is safely off")
    parser.add_argument("--serial", help="HackRF serial number")
    parser.add_argument("--root600-threshold", type=float, default=0.45)
    parser.add_argument("--root147-threshold", type=float, default=0.35)
    parser.add_argument("--queue-depth", type=int, default=4)
    parser.add_argument("--output", type=Path,
                        default=Path("live_droneid_results") /
                        datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--libhackrf", type=Path,
                        default=Path(ctypes.util.find_library("hackrf") or
                                     "/opt/homebrew/lib/libhackrf.dylib"))
    parser.add_argument("--turbo-binary", type=Path,
                        default=Path("build/remove_turbo_soft"))
    parser.add_argument("--replay", type=Path,
                        help="offline HackRF int8 IQ file instead of live hardware")
    parser.add_argument("--replay-freq", type=parse_frequency,
                        help="center frequency for --replay")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.dwell <= 0 or args.settle < 0:
        parser.error("dwell must be > 0 and settle must be >= 0")
    if not args.turbo_binary.exists():
        parser.error(f"Turbo decoder not found: {args.turbo_binary}")
    detector = DroneIDDetector(
        args.output, args.turbo_binary, args.root600_threshold,
        args.root147_threshold)
    try:
        if args.replay:
            return run_replay(args, detector)
        return run_live(args, detector)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        print(f"fatal: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
