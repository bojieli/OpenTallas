"""REHOST-1 2026-11-09: placement and ot-run-sealed respect each host's OWN ot-heavy load cap and its queued waiters.

Bug (COORD 09:2x): epyc7 had 44-53 waiters (1.9-2.3 TB) at load 123-186/96 while intel1/epyc4 admitted 300-600 GB.
epyc7's /etc/ot-heavy.conf sets LOAD_CAP_FACTOR=1.1 (cap 105), ot-run assumed 1.5 everywhere (cap 144), so at load
105-144 epyc7 "admitted now": SPILL never ran and REBALANCE re-placed onto epyc7.  ot-run-sealed pinned PLACE jobs to the
first host that held the kit whenever --status said "admits N GB" (memory only), behind the queue and the load cap."""
import importlib.machinery
import importlib.util
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent


def load(name, mod):
    loader = importlib.machinery.SourceFileLoader(mod, str(HERE / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    # LOADGATE_1110 (ot-heavy load gate) is covered by test_ot_run_load_gate.py; these cases pin the older rules with the gate off
    if hasattr(m, 'LOAD_GATE_FACTOR'):
        m.LOAD_GATE_FACTOR = 0
    return m


def row(admit, load, ncpu, cap=None):
    r = dict(admit_gb=admit, free_gb=admit, cpu_load1=load, ncpu=ncpu, total_gb=1000, disk_gb=1000, avail_gb=admit,
             headroom_gb=0, floor_gb=50, waiting=0, waiting_gb=0, running=1, fresh=0)
    if cap is not None:
        r["load_cap_factor"] = cap
    return r


class HostLoadCap(unittest.TestCase):
    def setUp(self):
        self.m = load("ot-run", "ot_run_lc")
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("OT_RUN_CRIT", None)
        os.environ.pop("OT_RUN_DIRECT", None)

    def tearDown(self):
        self.env.stop()

    def test_own_cap_holds(self):
        self.assertTrue(self.m.load_capped(row(900, 123, 96, cap=1.1), 48, 16))
        self.assertFalse(self.m.load_capped(row(900, 123, 96, cap=1.5), 48, 16))
        self.assertFalse(self.m.load_capped(row(900, 123, 96), 48, 16))       # old probe: fallback 1.5
        self.assertFalse(self.m.load_capped(row(900, 500, 96, cap=0), 48, 16))  # 0 = off

    def test_choose_leaves_capped_host(self):
        h, q = self.m.choose({"epyc7": row(900, 130, 96, cap=1.1), "epyc4": row(300, 60, 256)}, 48, 16)
        self.assertEqual((h, q), ("epyc4", False))

    def test_only_capped_host_queues(self):
        h, q = self.m.choose({"epyc7": row(900, 130, 96, cap=1.1)}, 48, 16)
        self.assertEqual((h, q), ("epyc7", True))

    def test_probe_line(self):
        self.assertEqual(self.m.loadcap_of("x\nOT_LOADCAP 1.1\n{}"), 1.1)
        self.assertIsNone(self.m.loadcap_of("OT_LOADCAP \n{}"))
        self.assertIsNone(self.m.loadcap_of("{}"))

    def test_probe_shell_reads_conf(self):
        with tempfile.TemporaryDirectory() as d:
            conf = os.path.join(d, "ot-heavy.conf")
            with open(conf, "w") as fh:
                fh.write("MIN_AVAIL_FRAC=0.15\nLOAD_CAP_FACTOR=1.5\nLOAD_CAP_FACTOR=1.1   # KW-FIX-42\n")
            out = subprocess.run(["sh", "-c", self.m.LOADCAP_SH.replace("/etc/ot-heavy.conf", conf)],
                                 capture_output=True, text=True).stdout
            self.assertEqual(self.m.loadcap_of(out), 1.1)
            out = subprocess.run(["sh", "-c", self.m.LOADCAP_SH.replace("/etc/ot-heavy.conf", conf + ".none")],
                                 capture_output=True, text=True).stdout
            self.assertIsNone(self.m.loadcap_of(out))

    def test_choose_selftest(self):
        self.assertFalse(self.m.choose_selftest())


def fake_backend(line):
    f = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
    f.write("#!/bin/sh\necho '%s'\n" % line)
    f.close()
    os.chmod(f.name, 0o755)
    return f.name


E7CAP = "epyc7 admits 104 GB (avail 200) load 123/96 waiters 45:1950 GB run 58 LOADCAP root 60%"
E7Q = "epyc7 admits 104 GB (avail 200) load 80/96 waiters 45:1950 GB run 58 root 60%"
E7OK = "epyc7 admits 300 GB (avail 400) load 40/96 run 10"
E4 = "epyc4 admits 296 GB (avail 408) load 54/256 run 18"
E2 = "epyc2 admits 215 GB (avail 384) load 55/128 run 49"


class SealedPick(unittest.TestCase):
    K = "/srv/opentallas-scratch2/claude/kw27-wave-1109/runs/s81/kit-wave/s81/x/items/t/attempt_1/gen/t"

    def setUp(self):
        self.m = load("ot-run-sealed", "ot_run_sealed_lc")

    def admits(self, line, mem=48):
        return self.m.admits(fake_backend("ot-run status: " + line), "epyc7", mem)

    def test_admits(self):
        self.assertFalse(self.admits(E2 + " | " + E7CAP))
        self.assertFalse(self.admits(E2 + " | " + E7Q))
        self.assertTrue(self.admits(E2 + " | " + E7OK))
        self.assertTrue(self.admits("epyc7 admits 104 GB load 80/96 waiters 1:48 GB run 58"))
        self.assertTrue(self.admits(E7OK + " | epyc2 admits 5 GB load 300/128 LOADCAP"))
        self.assertFalse(self.admits(E2 + " | epyc7 HELD (drain)"))

    def pick(self, status, have):
        R = os.path.dirname(self.K) + "/run_kit.sh"
        argv = ["--mem", "48", "--threads", "8", "--dir", self.K, "--", "bash", "-c", f"bash {R} {self.K} place 48 8"]
        conf = dict(enabled=True, dirs=["/srv/opentallas-scratch2/claude/kw27-wave-1109/runs/"],
                    hosts=["epyc7", "epyc2", "epyc4"], backend=fake_backend("ot-run status: " + status),
                    sealed_backend="/bin/true", spec_dir=tempfile.mkdtemp())
        out, why = self.m.decide(argv, conf, check=lambda h, r, k: (h in have, []))
        return out[out.index("--hosts") + 1] if out[0] == "/bin/true" else "UNSEALED"

    def test_pick(self):
        st = " | ".join([E2, E4, E7CAP])
        self.assertEqual(self.pick(st, {"epyc7"}), "UNSEALED")             # only holder capped: ot-run may spill
        self.assertEqual(self.pick(st, {"epyc7", "epyc4"}), "epyc4")
        self.assertEqual(self.pick(" | ".join([E2, E4, E7OK]), {"epyc7", "epyc2", "epyc4"}), "epyc4")  # lowest load/cores
        self.assertEqual(self.pick(" | ".join([E2, E4, E7OK]), {"epyc7"}), "epyc7")
        self.assertEqual(self.pick(" | ".join([E2, E4, E7OK]), set()), "UNSEALED")
        self.assertEqual(self.pick(" | ".join([E2, "epyc4 HELD (drain)", E7CAP]), {"epyc7", "epyc2", "epyc4"}), "epyc2")


if __name__ == "__main__":
    unittest.main()
