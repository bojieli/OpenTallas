"""ot-reaper GATE / UMBRELLA / HOSTS passes and the ot-run low-disk reaper trigger (ROOT-2130 2026-10-18, FLEET-DISK)."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


R = load("ot_reaper", HERE / "ot-reaper.py")


def age(p, hours):
    t = time.time() - hours * 3600
    for root, ds, fs in os.walk(p, topdown=False):
        for f in fs:
            os.utime(os.path.join(root, f), (t, t), follow_symlinks=False)
        os.utime(root, (t, t))


def mk(p, size=10):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        f.truncate(size)


def host_run(**kw):
    arg = dict(refs=[], dry=False, quiet_min=20, jobs={}, roots=[], hand_idle_h=48, hand=[], gate_roots=[],
               gate_idle_h=12, mentions="", umbrella_gb=0)
    arg.update(kw)
    r = subprocess.run([sys.executable, "-c", R.HOST_PY], input=json.dumps(arg), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


class GateTrim(unittest.TestCase):
    def test_idle_gate_loses_bulk_keeps_logs(self):
        with tempfile.TemporaryDirectory() as td:
            g = Path(td) / "ref_gate"
            old, young, ment = g / "kit_a-20261017T0100", g / "kit_b-20261018T2100", g / "kit_c-20261017T0100"
            for d in (old, young, ment):
                mk(d / "src/rtl/x.sv"); mk(d / "bin/tool"); mk(d / "orfs/6_final.odb", 30_000_000)
                mk(d / "gate.log"); mk(d / "gate_result.json"); mk(d / "gate_layout/die.png")
                mk(d / "small.odb", 1000)
            age(old, 13); age(ment, 13); age(young, 2)
            out = host_run(gate_roots=[str(g)], mentions="see kit_c-20261017T0100 for the verdict")
            self.assertFalse((old / "src").exists())
            self.assertFalse((old / "bin").exists())
            self.assertFalse((old / "orfs/6_final.odb").exists())
            for keep in ("gate.log", "gate_result.json", "gate_layout/die.png", "small.odb"):
                self.assertTrue((old / keep).exists(), keep)
            for d in (young, ment):
                self.assertTrue((d / "src/rtl/x.sv").exists())
                self.assertTrue((d / "orfs/6_final.odb").exists())
            self.assertTrue((old / ".ot_gate_trimmed").exists())
            self.assertIn("TOTAL", out)

    def test_keep_and_live_ref_are_kept(self):
        with tempfile.TemporaryDirectory() as td:
            g = Path(td) / "ref_gate"
            k, r = g / "kit_k-1", g / "kit_r-1"
            for d in (k, r):
                mk(d / "src/a.sv")
            mk(k / ".keep")
            age(g, 30)
            host_run(gate_roots=[str(g)], refs=[str(r) + "/src/a.sv"])
            self.assertTrue((k / "src/a.sv").exists())
            self.assertTrue((r / "src/a.sv").exists())


class Umbrella(unittest.TestCase):
    def test_children_aged_one_by_one(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "claude"
            u = root / "qwen-kvsys"
            for c in ("old1", "old2", "kept", "young", "mentioned"):
                mk(u / c / "data.bin", 1000)
            mk(u / "kept/.keep")
            age(u, 60)
            age(u / "young", 1)
            out = host_run(hand=[(str(root), R.HAND_NEVER)], umbrella_gb=1, mentions="wt mentioned is pending")
            self.assertFalse((u / "old1").exists(), out)
            self.assertFalse((u / "old2").exists())
            for c in ("kept", "young", "mentioned"):
                self.assertTrue((u / c).exists(), c)
            self.assertIn("UMBRELLA", out)

    def test_whole_idle_hand_dir_still_reaped_and_snapshots_never(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "claude"
            mk(root / "scratch1/x.bin")
            mk(root / "flowhold/src/tools/x.py")
            mk(root / "ttbatch/26f14af32/tools/closure_loop/tt_overlay.py")
            age(root, 72)
            host_run(hand=[(str(root), R.HAND_NEVER)], umbrella_gb=1)
            self.assertFalse((root / "scratch1").exists())
            self.assertTrue((root / "flowhold/src/tools/x.py").exists())
            self.assertTrue((root / "ttbatch/26f14af32/tools/closure_loop/tt_overlay.py").exists())


class Hosts(unittest.TestCase):
    def test_hosts_follow_hosts_json_and_ot_run(self):
        with tempfile.TemporaryDirectory() as td:
            hj = Path(td) / "hosts.json"
            hj.write_text(json.dumps({"hosts": [{"name": "ot-new9"}, {"name": "localhost"}]}))
            otr = Path(td) / "ot-run"
            otr.write_text('HOSTS = ["ot-epyc4", "ot-run-only"]\n')
            with patch.object(R, "HOSTS_JSON", [str(hj)]), patch.object(R, "OT_RUN", str(otr)):
                hs = R.fleet_hosts()
        for h in ("ot-epyc4", "ot-epyc7", "ot-agidock128", "ot-pve1", "ot-new9", "ot-run-only"):
            self.assertIn(h, hs)
        self.assertNotIn("localhost", hs)
        self.assertEqual(len(hs), len(set(hs)))

    def test_early_fail_is_strippable(self):
        self.assertIn("EARLY_FAIL", R.FAIL)


class OtRunTrigger(unittest.TestCase):
    def test_low_disk_starts_reaper_once(self):
        otrun = load("ot_run_mod", HERE / "ot-run")
        with tempfile.TemporaryDirectory() as td:
            mark = Path(td) / "ran"
            fake = Path(td) / "fake_reaper.py"
            fake.write_text(f"import sys; open({str(mark)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n")
            with patch.object(otrun, "REAPER", str(fake)), \
                    patch.object(otrun, "REAP_STAMP", str(Path(td) / "stamp-{host}")):
                self.assertTrue(otrun.trigger_reaper("ot-x", "disk 5 GB < 20"))
                self.assertFalse(otrun.trigger_reaper("ot-x", "disk 5 GB < 20"))     # rate-limited
                for _ in range(100):
                    if mark.exists():
                        break
                    time.sleep(0.05)
            self.assertEqual(mark.read_text().split(), ["--host", "ot-x"])

    def test_missing_reaper_is_a_noop(self):
        otrun = load("ot_run_mod2", HERE / "ot-run")
        with patch.object(otrun, "REAPER", "/nonexistent/ot-reaper.py"):
            self.assertFalse(otrun.trigger_reaper("ot-x", "disk"))


if __name__ == "__main__":
    unittest.main()
