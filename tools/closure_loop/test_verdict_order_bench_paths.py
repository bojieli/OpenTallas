"""drive-0212 2026-10-09: verdict checks that read the collect stage's {RUN}/record, and bench files outside the sync."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import closure_loop as cl  # noqa: E402

COLLECT = ("mkdir -p {RUN}/record && cd {SRC} && python3 tools/x_export.py --out {RUN}/record; "
           "python3 tools/s81_die_view_ports.py check --lef {RUN}/record/m.lef > {RUN}/record/check.json")
LEF_CHECK = {"name": "lef_check_MATCH",
             "cmd": "python3 -c \"import json,sys; sys.exit(json.load(open('{RUN}/record/check.json'))['verdict'] != 'MATCH')\""}


def spec(checks=(LEF_CHECK,), collect=COLLECT, bench=()):
    return {"name": "j", "block": "b", "owner": "o", "source": {"branch": "main", "commit": "abcdef1"},
            "stages": {"route": {"cmd": "true"}, "collect": {"cmd": collect}, "bench": list(bench)},
            "verdict": {"corner_sta": "x", "drc_metrics": "y", "checks": list(checks)}}


class PreCollect(unittest.TestCase):
    def test_cmd(self):
        self.assertEqual(cl.precollect_cmd(spec()), COLLECT)
        self.assertIsNone(cl.precollect_cmd(spec(checks=[{"name": "c", "cmd": "test -s {CL}/ttb_corner.txt"}])))
        self.assertIsNone(cl.precollect_cmd(spec(collect="cp {RUN}/routes/x {RUN}/out/")))

    def test_verdict_runs_collect_before_the_check(self):
        j = {"name": "j", "spec": spec(), "run": "/r", "host": "h", "events": [], "status": "READY"}
        calls = []

        def ro(job, cmd, timeout=300):
            calls.append(cmd)
            return True, ""
        with patch.object(cl, "adoption_held", return_value=False), patch.object(cl, "get_metrics", return_value={}), \
                patch.object(cl, "remote_ok", side_effect=ro), patch.object(cl, "finish"), patch.object(cl, "log"):
            cl.do_verdict(j, None, [])
        self.assertEqual(calls, [COLLECT, LEF_CHECK["cmd"]])
        self.assertEqual(j["failed_checks"], [])


class FakeGit:
    def __init__(self, files):
        self.files = files

    def show(self, commit, path):
        return self.files.get(path)

    def blob(self, commit, path):
        return "b" if path in self.files else None


class BenchPaths(unittest.TestCase):
    BENCH = [{"name": "p", "expect": "pass", "cmd": "bash physical/phys_intake/bench.sh ta15 pos {RUN}/bench_pos"}]
    SCRIPT = ("case $1 in ta15) C=rtl/hbm_accel/control; T=tests/rtl/tb_ta15.sv;\n"
              "  iverilog -o {RUN}/x/a.out $C/top.sv $T results/rtl/tr/trace.hex missing/never.sv ;; esac\n")

    def git(self):
        return FakeGit({"physical/phys_intake/bench.sh": self.SCRIPT, "tests/rtl/tb_ta15.sv": "",
                        "results/rtl/tr/trace.hex": "", "rtl/hbm_accel/control/top.sv": ""})

    def test_missing_dirs(self):
        self.assertEqual(cl.bench_missing_paths(spec(bench=self.BENCH), self.git()), ["results/rtl/tr", "tests/rtl"])

    def test_already_synced(self):
        s = spec(bench=self.BENCH)
        s["source"]["extra_paths"] = ["tests", "results/rtl/tr"]
        self.assertEqual(cl.bench_missing_paths(s, self.git()), [])

    def test_intake_adds_extra_paths(self):
        j = {"name": "j", "spec": spec(bench=self.BENCH), "events": []}
        with patch.object(cl, "bench_missing_paths", return_value=["tests/rtl"]), patch.object(cl, "log"):
            cl.bench_paths_at_submit(j)
        self.assertEqual(j["spec"]["source"]["extra_paths"], ["tests/rtl"])
        self.assertNotIn("extra_paths", j["spec_submitted"]["source"])


if __name__ == "__main__":
    unittest.main()
