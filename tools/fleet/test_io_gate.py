"""E11-IO-STALL-1124 (COORD hub 48a3b0f1): IO-pressure gate for fork / copy / seal jobs, fork worker cap + one fork per source disk, no lane_quota scan on a gated host."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import io_gate  # noqa: E402


def psi(path, some60):
    Path(path).write_text(f"some avg10=1.00 avg60={some60:.2f} avg300=1.00 total=1\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=1\n")
    return str(path)


def load_fork():
    loader = importlib.machinery.SourceFileLoader("ot_tree_fork_iog", str(HERE / "ot-tree-fork"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_tree_fork_iog", loader))
    loader.exec_module(m)
    return m


class Classify(unittest.TestCase):
    def test_bulk_commands(self):
        for argv in (["python3", "-I", "/x/rt/current/tools/fleet/ot-tree-fork", "/a", "/b"],
                     ["python3", "-I", "-u", "/x/tools/autopilot/src_manifest.py", "replicate", "/p"],
                     ["bash", "-c", "set -e\ncd /k && tar -C /k -cf - . | ssh h tar -xf -"],
                     ["bash", "-c", "ionice -c3 nice -n 19 timeout 600 rsync -a a/ b/"],
                     ["bash", "/x/copy.sh"] and ["bash", "-c", "cp -a /src /dst"],
                     ["bash", "-c", "OT_LANE=X ./fork_bound.sh a b"]):
            self.assertTrue(io_gate.is_bulk(argv), argv)

    def test_text_that_only_mentions_a_name_is_not_bulk(self):
        for argv in (["bash", "-c", "python3 -I - <<'PY'\nimport json\ncommand=\"tar -C \"+x\n    return seal(directory)\nPY"],
                     ["python3", "-I", "/x/tools/autopilot/src_manifest.py", "verify", "/p"],
                     ["bash", "/x/run_kit.sh", "/k", "route"], ["openroad", "-exit", "fork_test.tcl"], ["cp", "a", "b"]):
            self.assertFalse(io_gate.is_bulk(argv), argv)

    def test_gated_reads_some_avg60(self):
        with tempfile.TemporaryDirectory() as d:
            p = psi(os.path.join(d, "io"), 33.48)
            self.assertEqual(io_gate.gated(p, 20), (True, 33.48, 20))
            self.assertFalse(io_gate.gated(psi(p, 12.0), 20)[0])
            self.assertFalse(io_gate.gated(psi(p, 99.0), 0)[0])                 # 0 disables
            self.assertFalse(io_gate.gated(os.path.join(d, "none"), 20)[0])     # no PSI: never gated


class Heavy(unittest.TestCase):
    def setUp(self):
        self.d = d = Path(tempfile.mkdtemp())
        (d / "bin").mkdir()

        def w(name, body):
            p = d / "bin" / name
            p.write_text("#!/bin/bash\n" + body + "\n")
            p.chmod(0o755)
            return p
        self.rec = w("reconcile", '[ "$1" = --is-die ] && exit 1; [ "$1" = --is-plan ] && exit 1; [ "$1" = --is-proof ] && exit 1; echo "OK 4 cls | need 4, available 100 GB, growth charged 0 GB"')
        self.prot = w("protect", "exit 1")
        w("systemd-run", 'printf "%s\\n" "$@" > "$OUT_ARGS"')
        s = (HERE / "ot-heavy").read_text()
        s = s.replace("/usr/local/bin/ot-heavy-reconcile", str(self.rec)).replace("/usr/local/bin/ot-protect-die", str(self.prot))
        s = s.replace("D=/var/tmp/ot-heavy", f"D={d}/state").replace("/etc/ot-heavy.conf", str(d / "conf")).replace("/usr/local/lib/ot-heavy", str(d / "nolib"))
        s = s.replace("sleep 20", "sleep 0.2").replace("sleep 5;", "sleep 0.2;")
        self.h = d / "ot-heavy"
        self.h.write_text(s)
        self.h.chmod(0o755)
        (d / "conf").write_text("LOAD_GATE_FACTOR=0\nLOAD_CAP_FACTOR=0\nTHREAD_CAP_FACTOR=0\n")
        (d / "state").mkdir()
        self.psi = d / "io"

    def run_(self, cmd, some60, extra=None):
        psi(self.psi, some60)
        env = dict(os.environ, PATH=f"{self.d}/bin:" + os.environ["PATH"], OUT_ARGS=str(self.d / "args"), OT_VL_JCAP="0", OT_HEAVY_SYSTEM_TOOLS="1",
                   OT_HEAVY_THREADS="2", OT_IO_PSI=str(self.psi), OT_IO_GATE_PY=str(HERE / "io_gate.py"), OT_HEAVY_SHORT_POOL="0")
        for k in ("OT_HEAVY_CPU", "OT_HEAVY_PRIO", "OT_HEAVY_CONF", "OT_HEAVY_DIRECT", "OT_HEAVY_PARENT_UNIT", "OT_HEAVY_IO", "IO_GATE_SOME", "IO_GATE_MAX_WAIT_S"):
            env.pop(k, None)
        env.update(extra or {})
        try:
            (self.d / "args").unlink()
        except FileNotFoundError:
            pass
        r = subprocess.run([str(self.h), "--mem", "4", "--max-wait", "1", "--", *cmd], capture_output=True, text=True, env=env, timeout=60)
        return r, (self.d / "args").exists()

    FORK = ["python3", "-I", "/x/tools/fleet/ot-tree-fork", "/a", "/b"]

    def test_fork_waits_while_io_pressure_is_high(self):
        r, ran = self.run_(self.FORK, 33.5)
        self.assertFalse(ran)
        self.assertEqual(r.returncode, 75)
        self.assertIn("io gate: /proc/pressure/io some avg60 33.50 > IO_GATE_SOME 20", r.stderr)
        self.assertIn("waiting for io", r.stderr)

    def test_fork_runs_under_the_threshold_and_other_jobs_never_wait(self):
        self.assertTrue(self.run_(self.FORK, 12.0)[1])
        r, ran = self.run_(["bash", "/x/run_kit.sh", "/k", "route"], 90.0)
        self.assertTrue(ran, r.stderr)

    def test_off_switch_explicit_class_child_and_max_wait(self):
        self.assertTrue(self.run_(self.FORK, 90.0, {"IO_GATE_SOME": "0"})[1])
        self.assertFalse(self.run_(["bash", "/x/a.sh"], 90.0, {"OT_HEAVY_IO": "bulk"})[1])      # declared bulk
        self.assertTrue(self.run_(self.FORK, 90.0, {"OT_HEAVY_IO": "none"})[1])
        (self.d / "state" / "res.oth-p").write_text("oth-p 1\n")
        self.assertTrue(self.run_(self.FORK, 90.0, {"OT_HEAVY_PARENT_UNIT": "oth-p"})[1])         # child of an admitted unit
        r, ran = self.run_(self.FORK, 90.0, {"IO_GATE_MAX_WAIT_S": "0"})
        self.assertTrue(ran, r.stderr)
        self.assertIn("admitted anyway", (self.d / "state" / "admit.log").read_text())


class Fork(unittest.TestCase):
    def test_worker_count_is_capped_at_two(self):
        m = load_fork()
        self.assertEqual([m.fork_jobs(j) for j in (0, 1, 4, 32)], [2, 1, 2, 2])
        os.environ["OT_TREE_FORK_MAX_JOBS"] = "6"
        try:
            self.assertEqual(m.fork_jobs(0), 6)
        finally:
            del os.environ["OT_TREE_FORK_MAX_JOBS"]

    def test_one_fork_per_source_disk(self):
        m = load_fork()
        with tempfile.TemporaryDirectory() as d:
            with m.SrcDiskLock(d, lock_dir=os.path.join(d, "locks"), out=lambda *_: None):
                lines = []
                with self.assertRaises(m.Busy):
                    with m.SrcDiskLock(d, lock_dir=os.path.join(d, "locks"), wait_s=0.3, poll_s=0.1, out=lines.append):
                        pass
                self.assertIn("one per source disk", lines[0])
            with m.SrcDiskLock(d, lock_dir=os.path.join(d, "locks"), wait_s=0):          # released: the next fork goes
                pass

    def test_a_real_fork_still_copies(self):
        m = load_fork()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            (src / "a").mkdir(parents=True)
            (src / "a" / "f.txt").write_text("x")
            os.environ["OT_TREE_COPY_LOCK_DIR"] = os.path.join(d, "locks")
            try:
                m.COPY_LOCK_DIR = os.path.join(d, "locks")
                m.fork(str(src), str(Path(d) / "dst"), 8, out=lambda *_: None)
            finally:
                del os.environ["OT_TREE_COPY_LOCK_DIR"]
            self.assertEqual((Path(d) / "dst" / "a" / "f.txt").read_text(), "x")


class Quota(unittest.TestCase):
    def test_scan_is_skipped_on_a_gated_host(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, OT_IO_PSI=psi(os.path.join(d, "io"), 40.0), IO_GATE_SOME="20")
            r = subprocess.run([sys.executable, "-I", str(HERE / "lane_quota.py"), "scan"], capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual((r.returncode, json.loads(r.stdout)), (0, {}))
            self.assertIn("IO-GATED", r.stderr)


if __name__ == "__main__":
    unittest.main()
