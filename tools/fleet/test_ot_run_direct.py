"""DIRECT_1107 (OWNER 11-07): ot-run --direct places on real free memory and ot-heavy starts it on MemAvailable >= mem + 32 GB."""
import importlib.machinery
import importlib.util
import os
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_direct", str(HERE / "ot-run"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    m.LOAD_GATE_FACTOR = 0   # LOADGATE_1110 (load 300 on 128 threads is gated) is tested in test_ot_run_load_gate.py; these cases pin the memory rules
    return m


def row(admit, avail, load=300.0):
    return dict(admit_gb=admit, free_gb=admit, avail_gb=avail, cpu_load1=load, ncpu=128, total_gb=1000, disk_gb=1000,
                headroom_gb=0, floor_gb=50, waiting=0, waiting_gb=0, running=1, fresh=0)


class Choose(unittest.TestCase):
    def setUp(self):
        self.m = load()
        os.environ.pop("OT_RUN_DIRECT", None)
        self.addCleanup(os.environ.pop, "OT_RUN_DIRECT", None)

    def test_most_real_free_memory_wins(self):
        os.environ["OT_RUN_DIRECT"] = "1"
        self.assertEqual(self.m.choose({"a": row(-50, 300), "b": row(500, 200, load=1.0)}, 48), ("a", False))

    def test_headroom_is_the_floor(self):
        os.environ["OT_RUN_DIRECT"] = "1"
        self.assertEqual(self.m.choose({"a": row(500, 79), "b": row(500, 80)}, 48), ("b", False))
        self.assertEqual(self.m.choose({"a": row(500, 79), "b": row(500, 70)}, 48), ("a", True))    # waits, no start

    def test_a_load_gated_host_is_not_chosen_for_a_direct_job(self):
        # LOADGATE_1110: ot-heavy holds even --direct jobs on a host over 1.25 x nproc, so choose() must queue instead of picking it
        os.environ["OT_RUN_DIRECT"] = "1"
        m = load()
        m.LOAD_GATE_FACTOR = 1.25
        host, queue = m.choose({"a": row(500, 400, load=300.0), "b": row(500, 400, load=10.0)}, 48)
        self.assertEqual((host, queue), ("b", False))
        host, queue = m.choose({"a": row(500, 400, load=300.0)}, 48)
        self.assertTrue(queue)

    def test_off_by_default(self):
        self.assertEqual(self.m.choose({"a": row(-50, 300), "b": row(500, 200, load=1.0)}, 48)[0], "b")


class Heavy(unittest.TestCase):
    def test_block_sits_after_the_gates_and_keeps_the_floor(self):
        s = (HERE / "ot-heavy").read_text()
        self.assertLess(s.index("LOADCAP_1101 (FLOW-21"), s.index('if [ "${OT_HEAVY_DIRECT:-}" = 1 ]'))
        self.assertLess(s.index('if [ "${OT_HEAVY_DIRECT:-}" = 1 ]'), s.index('if [ "$V" = OK ]; then\n    echo "$UNIT $RES"'))
        self.assertIn('-ge $(( MEM + 32 ))', s)


class FreshOnly(unittest.TestCase):
    """DIRECT_MEMAVAIL_1110: only young direct records are charged; started jobs are already in MemAvailable."""

    def run_block(self, avail_gb, mem, records):
        import subprocess, tempfile, time
        s = (HERE / "ot-heavy").read_text()
        a = s.index('  if [ "${OT_HEAVY_DIRECT:-}" = 1 ]; then')
        b = s.index('  [ "$RES" != "$MEM" ]', a)
        d = tempfile.mkdtemp()
        for i, (req, age, active) in enumerate(records):
            f = os.path.join(d, f"direct.u{i}{'a' if active else 'i'}")
            open(f, "w").write(f"u{i}{'a' if active else 'i'} {req}\n")
            t = time.time() - age
            os.utime(f, (t, t))
        bindir = tempfile.mkdtemp()
        open(os.path.join(bindir, "systemctl"), "w").write('#!/bin/bash\ncase "$*" in *a.scope*) exit 0;; esac; exit 3\n')
        open(os.path.join(bindir, "awk"), "w").write(f'#!/bin/bash\necho {avail_gb}\n')
        for x in ("systemctl", "awk"): os.chmod(os.path.join(bindir, x), 0o755)
        sh = f'D={d}; MEM={mem}; UNIT=new; V=NO; RES=0; WHY=gate; OT_HEAVY_DIRECT=1\n' + s[a:b] + 'echo "$V|$WHY"\n'
        env = dict(os.environ, PATH=bindir + ":" + os.environ["PATH"])
        out = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, env=env).stdout.strip()
        return out, sorted(os.listdir(d))

    def test_old_direct_jobs_are_not_subtracted(self):
        out, _ = self.run_block(222, 96, [(64, 3 * 3600, True), (96, 2 * 3600, True), (32, 1800, True)])
        self.assertTrue(out.startswith("OK|"), out)

    def test_fresh_record_is_charged_full(self):
        out, _ = self.run_block(222, 96, [(96, 30, True)])
        self.assertTrue(out.startswith("NO|"), out)           # 222 - 96 < 96 + 32
        out, _ = self.run_block(222, 96, [(96, 30, False)])   # written but not started yet: still charged
        self.assertTrue(out.startswith("NO|"), out)

    def test_floor_is_32(self):
        self.assertTrue(self.run_block(128, 96, [])[0].startswith("OK|"))
        self.assertTrue(self.run_block(127, 96, [])[0].startswith("NO|"))

    def test_stale_inactive_record_is_dropped(self):
        out, left = self.run_block(222, 96, [(96, 600, False)])
        self.assertTrue(out.startswith("OK|"), out)
        self.assertEqual(left, ["direct.new"])
