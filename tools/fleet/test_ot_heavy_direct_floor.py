"""DIRECTFLOOR_1114 (ADMIT-TUNE-1): --direct needs MemAvailable >= MEM + max(32, INV_HEADROOM_GB), not a fixed 32 GB."""
import pathlib
import re
import subprocess
import unittest

SRC = pathlib.Path(__file__).with_name("ot-heavy").read_text()
M = re.search(r"^ *_dfloor=.*$", SRC, re.M)
C = re.search(r"^ *if \[ \$\(\( _avail - _pend \)\) -ge \$\(\( MEM \+ _dfloor \)\) \]; then$", SRC, re.M)


def ok(avail, mem, headroom):
    script = f"MEM={mem}; _avail={avail}; _pend=0; INV_HEADROOM_GB={headroom}\n{M.group(0)}\n{C.group(0)}\necho YES\nelse\necho NO\nfi\n"
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True).stdout.strip() == "YES"


class DirectFloor(unittest.TestCase):
    def test_snippet_is_present(self):
        self.assertTrue(M and C)

    def test_floor_96_needs_mem_plus_96(self):
        self.assertTrue(ok(18 + 96, 18, 96))
        self.assertFalse(ok(18 + 95, 18, 96))

    def test_small_or_missing_floor_keeps_the_old_32_gb(self):
        self.assertTrue(ok(18 + 32, 18, 16))
        self.assertFalse(ok(18 + 31, 18, 16))
        self.assertFalse(ok(18 + 31, 18, ""))


if __name__ == "__main__":
    unittest.main()
