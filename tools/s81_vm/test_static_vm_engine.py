import unittest

from static_vm_engine import DLAT, arm_arg, check_arg, validate


def arm(t, s, base, n, cl="su"):
    return dict(cycle=t, kind="arm", slot=s, client=cl, base_row=base, nrows=n)


def chk(t, s, cl="su"):
    return dict(cycle=t, kind="check", slot=s, client=cl)


class StaticVmEngine(unittest.TestCase):
    def test_encoding_matches_rtl_fields(self):
        self.assertEqual(arm_arg(2, "hc", 32, 17) >> 21, 2)
        self.assertEqual((arm_arg(2, "hc", 32, 17) >> 20) & 1, 1)
        self.assertEqual((arm_arg(0, "su", 32, 17) >> 10) & 0x3FF, 2)
        self.assertEqual(arm_arg(0, "su", 32, 17) & 0x3FF, 16)
        self.assertEqual(check_arg(3, "su") & 0xFFFFF, 0xFFFFF)
        with self.assertRaises(ValueError):
            arm_arg(0, "su", 8, 4)

    def test_clean_calendar(self):
        cmds = [arm(10, 0, 0, 2), chk(20, 0), arm(21, 0, 32, 1), chk(30, 0)]
        commits = [(11, 0), (12, 1), (22, 32)]
        done, err = validate(cmds, commits, reads=[(21, 0)])
        self.assertEqual(err, [])
        self.assertEqual(done[0], 10 + DLAT)

    def test_faults_rejected(self):
        self.assertTrue(any("[4]" in e for e in validate([arm(1, 0, 0, 1), arm(2, 0, 16, 1), chk(9, 0)], [(3, 16)])[1]))
        self.assertTrue(any("[5]" in e for e in validate([arm(1, 0, 0, 32), arm(2, 1, 16, 1), chk(9, 0), chk(10, 1)])[1]))
        self.assertTrue(any("[2]" in e for e in validate([chk(1, 0)])[1]))
        self.assertTrue(any("[3]" in e for e in validate([arm(1, 0, 0, 1), chk(5, 0, "hc")], [(2, 0)])[1]))
        self.assertTrue(any("[0]" in e for e in validate([arm(1, 0, 0, 2), chk(5, 0)], [(2, 0)])[1]))
        self.assertTrue(any("[7]" in e for e in validate([arm(1, 0, 0, 1), chk(5, 0)], [(2, 0)], [(5, 0)])[1]))
        self.assertTrue(any("ARM cycle" in e for e in validate([arm(1, 0, 0, 1), chk(5, 0)], [(1, 0), (2, 0)])[1]))


if __name__ == "__main__":
    unittest.main()
