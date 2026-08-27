# SPDX-License-Identifier: GPL-3.0-or-later

import importlib.util
import struct
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "o4_packet_tool.py"
SPEC = importlib.util.spec_from_file_location("o4_packet_tool", MODULE_PATH)
o4 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(o4)


class O4PacketToolTests(unittest.TestCase):
    def test_sm2_generator_is_on_curve(self):
        gx = bytes.fromhex(
            "32C4AE2C1F1981195F9904466A39C994"
            "8FE30BBFF2660BE1715A4589334C74C7"
        )
        gy = bytes.fromhex(
            "BC3736A2F4F6779C59BDCEE36B692153"
            "D0A9877CC62A474002DF32E52139F0A0"
        )
        self.assertTrue(o4.sm2_point_valid(gx + gy))

    def test_crc_append_has_zero_remainder(self):
        body = b"synthetic O4 research packet"
        crc = o4.dji_crc16(body)
        packet = body + struct.pack("<H", crc)
        self.assertEqual(o4.dji_crc16(packet), 0)

    def test_note_length_is_rejected_before_decrypt(self):
        packet = bytearray(138)
        packet[0:10] = b"\x87\x10INFP" + bytes.fromhex("01020304")
        packet[18:20] = struct.pack("<H", 1)
        with self.assertRaisesRegex(ValueError, "exactly 16 bytes"):
            o4.decrypt_87(bytes(packet), "00")


if __name__ == "__main__":
    unittest.main()

