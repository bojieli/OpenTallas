"""The fleet host lists in ot-run, ot-sizes-sync, ot-reserve (and ot-autoclean) must agree: epyc4/7/8/9 present, retired epyc5/epyc6 absent
(KW-FIX-44 11-09 terminations, ONBOARD-EPYC9 11-11)."""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEED = {"epyc2", "epyc4", "epyc7", "epyc8", "epyc9", "intel1"}
RETIRED = {"epyc5", "epyc6"}


def hosts_of(fname, pat):
    t = (HERE / fname).read_text()
    m = re.search(pat, t, re.M)
    assert m, fname
    return set(re.findall(r'[a-z]+[0-9]*', m.group(1))) if False else set(re.findall(r'"([a-z0-9-]+)"', m.group(1))) or set(m.group(1).split(","))


class HostLists(unittest.TestCase):
    def check(self, got, name):
        self.assertTrue(NEED <= got, f"{name} lacks {sorted(NEED - got)}")
        self.assertFalse(RETIRED & got, f"{name} still lists {sorted(RETIRED & got)}")

    def test_ot_run(self):
        self.check(hosts_of("ot-run", r'^HOSTS = \[([^\]]*)\]'), "ot-run HOSTS")

    def test_ot_sizes_sync(self):
        self.check(hosts_of("ot-sizes-sync", r'^HOSTS = \[([^\]]*)\]'), "ot-sizes-sync HOSTS")

    def test_ot_reserve(self):
        self.check(hosts_of("ot-reserve", r'"OT_RESERVE_HOSTS", "([^"]*)"'), "ot-reserve default hosts")

    def test_ot_autoclean(self):
        self.check(hosts_of("ot-autoclean.py", r'^HOSTS = \[([^\]]*)\]'), "ot-autoclean HOSTS")


if __name__ == "__main__":
    unittest.main()
