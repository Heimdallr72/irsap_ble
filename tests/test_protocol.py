"""Protocol tests built from real captures (no Home Assistant needed).

Run: python3 -m unittest discover -s tests   (from the irsap_ble folder, with PYTHONPATH=custom_components/irsap_ble/..)
"""
import importlib.util
from pathlib import Path
import unittest
import zlib

spec = importlib.util.spec_from_file_location(
    "irsap_protocol", Path(__file__).parent.parent / "custom_components" / "irsap_ble" / "protocol.py"
)
protocol = importlib.util.module_from_spec(spec)
import sys
sys.modules["irsap_protocol"] = protocol
spec.loader.exec_module(protocol)

# State records as read from a real radiator (tail of the data returned by the status characteristic)
PROGRAM_ON = (
    "0021011002" "0121011001" "02210120320321022 0b40004210220c80005210220f00006210220e1000721041"
    "0f02ce16a08210220c80009218c4001" "0a210220f1000b210220e1000c210410f02ce16a0d210110000e"
).replace(" ", "")
OFF = (
    "0021011002" "0121011000" "0221012032032102 20b40004210220c80005210220f00006210220f00007210110000821"
    "0220c80009218c4001" "0a210220f2000b210120320c210410ffffffff0d210110000e"
).replace(" ", "")
MANUAL = (
    "0021011001" "0121011001" "022101203203210220b40004210220c80005210220dc0006210220f000072101100008"
    "210220c80009218c4001" "0a210220f1000b210220dc000c210410ffffffff0d210110000e"
).replace(" ", "")


# Full state areas read from a real radiator (Ares): temporary 24.0 C for 2 h, and plain program
TIMED_24_2H = "00210110020121011001022101203203210220b40004210220c80005210220f00006210220f000072104106059ea6a08210220c80009218c40010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff0a210220fb000b210220f0000c2104106059ea6a0d210110000e210110ff0f210210ffff10210210ffff11210110001221012002132101200014210120001521011000162101100017210110011821011000192102100807003101101c013101105702310410057ee96a0331021090010431011000053101104606310110000731011000083101100009310110000a310220ff7f0041011000014101100002410440000000000341044000000000044101100005410040064104400000000007410410ffffffff08410110000941011000613670a4"
PROGRAM_PLAIN = "00210110020121011001022101203203210220b40004210220c80005210220f00006210220f000072101100008210220c80009218c40010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff0a210220fb000b210220f0000c210410504bea6a0d210110000e210110ff0f210210ffff10210210ffff11210110001221012002132101200014210120001521011000162101100017210110011821011000192102100807003101101c013101105702310410057ee96a0331021090010431011000053101104606310110000731011000083101100009310110000a310220ff7f0041011000014101100002410440000000000341044000000000044101100005410040064104400000000007410410ffffffff084101100009410110004f56a8a8"


class TestProtocol(unittest.TestCase):
    def test_crc_and_lengths(self):
        for cmd in (1, 2, 3, 4):
            announce, blob = protocol.build_command(cmd, temp=22.0 if cmd in (3, 4) else None, hours=2 if cmd == 3 else None)
            self.assertEqual(zlib.crc32(blob[:-4]).to_bytes(4, "little"), blob[-4:])
            self.assertEqual(int.from_bytes(announce[4:6], "little"), len(blob))
            self.assertEqual(len(announce), 44)

    def test_manual_sets_record_05_only(self):
        _, blob = protocol.build_command(4, temp=21.5, now=1793130000)
        self.assertIn(bytes.fromhex("05210220d700"), blob)
        self.assertEqual(blob[107], 1)  # mode record = manual
        self.assertEqual(blob[112], 1)  # on

    def test_program_comfort(self):
        _, blob = protocol.build_command(2, now=1793130000)
        self.assertIn(bytes.fromhex("05210220f000"), blob)
        _, blob = protocol.build_command(2, comfort=23.5, now=1793130000)
        self.assertIn(bytes.fromhex("05210220eb00"), blob)
        self.assertEqual(blob[107], 2)  # program

    def test_off(self):
        _, blob = protocol.build_command(1, now=1793130000)
        self.assertEqual(blob[112], 0)

    def test_temporary_expiry_rounded_to_hour(self):
        _, blob = protocol.build_command(3, temp=22.5, hours=12, now=1793130000)
        k = blob.find(bytes.fromhex("07210410"))
        expiry = int.from_bytes(blob[k + 4 : k + 8], "little")
        self.assertEqual(expiry % 3600, 0)
        self.assertEqual(expiry, (1793130000 + 12 * 3600) // 3600 * 3600)
        self.assertIn(bytes.fromhex("06210220e100"), blob)

    def test_status_requests(self):
        reqs = protocol.build_status_requests(now=1793130000)
        self.assertEqual([len(r) for r in reqs], [44, 44])
        self.assertEqual(reqs[0][:4], bytes([0, 0, 0, 1]))
        self.assertEqual(reqs[1][:4], bytes([2, 0, 0, 1]))

    def test_parse_program(self):
        st = protocol.parse_state(b"\0" * 10 + bytes.fromhex(PROGRAM_ON))
        self.assertEqual((st.mode, st.is_on, st.current_temp, st.target_temp), ("program", True, 24.1, 22.5))
        self.assertIsNotNone(st.expiry)
        self.assertEqual(st.presets, {"antifreeze": 5.0, "eco": 18.0, "comfort": 24.0})

    def test_parse_off(self):
        st = protocol.parse_state(b"\0" * 10 + bytes.fromhex(OFF))
        self.assertEqual((st.mode, st.is_on, st.current_temp, st.target_temp, st.expiry), ("program", False, 24.2, 5.0, None))

    def test_parse_manual(self):
        st = protocol.parse_state(b"\0" * 10 + bytes.fromhex(MANUAL))
        self.assertEqual((st.mode, st.is_on, st.target_temp, st.expiry), ("manual", True, 22.0, None))

    def test_timed_mode_real_captures(self):
        from datetime import timedelta
        t = protocol.parse_state(b"\0" * 10 + bytes.fromhex(TIMED_24_2H))      # temporary 24.0 C, equal to Comfort
        p = protocol.parse_state(b"\0" * 10 + bytes.fromhex(PROGRAM_PLAIN))    # plain program, same setpoint
        self.assertEqual((t.mode, t.target_temp, p.mode, p.target_temp), ("program", 24.0, "program", 24.0))
        self.assertIsNotNone(t.timed_until)
        self.assertIsNone(p.timed_until)
        self.assertTrue(protocol.is_timed(t, t.timed_until - timedelta(hours=1)))
        self.assertFalse(protocol.is_timed(t, t.timed_until + timedelta(minutes=1)))   # the timer has ended
        self.assertFalse(protocol.is_timed(p, p.expiry - timedelta(hours=1)))
        self.assertTrue(protocol.is_timed(protocol.parse_state(b"\0" * 10 + bytes.fromhex(MANUAL))))
        self.assertFalse(protocol.is_timed(protocol.parse_state(b"\0" * 10 + bytes.fromhex(OFF))))

    def test_parse_garbage(self):
        self.assertIsNone(protocol.parse_state(b"\x01\x02\x03"))


# Real state area (Ares) after the app removed the Monday-Friday 06:00-09:00 Comfort slot: the program record is
# shorter (0x6e bytes instead of 0x8c). Days are Sunday, Monday..Friday, Saturday.
PROGRAM_EDITED = "00210110020121011000022101203203210220b40004210220c80005210220f00006210220f000072101100008210220c80009216e40010600020900010c00020e0001120002160001ff010c00020e0001120002160001ff010c00020e0001120002160001ff010c00020e0001120002160001ff010c00020e0001120002160001ff010c00020e0001120002160001ff010600020900010c00020e0001120002160001ff0a210220e9000b210120320c210410ffffffff0d210110000e210110ff0f210210ffff10210210ffff1121011000122101200213210120001421012000152101100016210110001721011001182101100019210210080700310110a2013101100002310410a674ed6a0331021090010431011000053101104906310110000731011000083101100009310110000a310220ff7f0041011000014101100002410440000000000341044000000000044101100005410040064104400000000007410410ffffffff08410110000941011000a9027d0c"


class TestProgram(unittest.TestCase):
    def test_program_is_read_from_the_state(self):
        program = protocol.parse_state(bytes.fromhex(PROGRAM_EDITED)).program
        self.assertEqual(len(program), 0x6E)
        days = program.split(b"\xff")[:-1]
        self.assertEqual(len(days), 7)
        self.assertEqual(len(days[0]), 19)   # Sunday: 06:00 Comfort kept
        self.assertEqual(len(days[3]), 13)   # Wednesday: no 06:00 Comfort
        self.assertEqual(days[0], days[6])    # Saturday like Sunday

    def test_state_without_program_record(self):
        self.assertIsNone(protocol.find_program(bytes.fromhex(OFF[:60])))

    def test_template_program_is_a_no_op(self):
        template_program = protocol.find_program(bytes.fromhex(protocol.TEMPLATES[2]))
        self.assertEqual(len(template_program), 0x8C)
        for cmd in (1, 2, 3, 4):
            a = protocol.build_command(cmd, temp=22.0, hours=2, now=1_800_000_000) if cmd in (3, 4) else \
                protocol.build_command(cmd, now=1_800_000_000)
            b = protocol.build_command(cmd, temp=22.0, hours=2, program=template_program, now=1_800_000_000) \
                if cmd in (3, 4) else protocol.build_command(cmd, program=template_program, now=1_800_000_000)
            self.assertEqual(a, b)

    def test_command_carries_the_current_program(self):
        program = protocol.parse_state(bytes.fromhex(PROGRAM_EDITED)).program
        for cmd in (1, 2, 3, 4):
            kwargs = {"temp": 22.0, "hours": 2} if cmd == 3 else {"temp": 22.0} if cmd == 4 else {}
            announce, blob = protocol.build_command(cmd, program=program, now=1_800_000_000, **kwargs)
            template = bytes.fromhex(protocol.TEMPLATES[cmd])
            self.assertEqual(len(blob), len(template) - 30)
            self.assertEqual(protocol.find_program(blob), program)
            self.assertEqual(int.from_bytes(announce[4:6], "little"), len(blob))
            self.assertEqual(int.from_bytes(blob[41:43], "little"), len(blob) - 47)
            self.assertEqual(int.from_bytes(blob[-4:], "little"), zlib.crc32(blob[:-4]) & 0xFFFFFFFF)
            if cmd in (3, 4):   # these also change the temperature/expiry records, checked elsewhere
                continue
            # everything outside the program record is unchanged
            k = blob.find(bytes([9, 0x21, 0x6E, 0x40]))
            mask = lambda b: b[:52] + bytes(4) + b[56:]   # the second timestamp (52:56) is refreshed at each build
            self.assertEqual(mask(blob[:k])[43:], mask(template[:k])[43:])
            self.assertEqual(blob[k + 4 + 0x6E : -4], template[k + 4 + 0x8C : -4])


if __name__ == "__main__":
    unittest.main()
