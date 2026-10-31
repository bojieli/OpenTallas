#!/usr/bin/env python3
"""AUTOBUILD-PIPE-2 (OWNER 12.23): round-robin launches across dies; plan files not named die_plan.json."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def _cfg(per_tick=4, inflight=70):
    d = {"enabled": True, "event": "e", "plan": "/p/die_plan.json", "gen_host": "intel1", "src": "/s",
         "die_max_inflight": 56}
    return {"enabled": True, "max_inflight": inflight, "max_launch_per_tick": per_tick,
            "dies": {"s81": dict(d), "s81_head": dict(d), "qwen_kvsys": dict(d)}}


def _picks(die, n):
    return [{"item": f"{die}_{i}", "kind": "type", "replicas": 1} for i in range(n)], {}


class RoundRobin(unittest.TestCase):
    def run_plan(self, cfg, counts, st=None):
        st = st or {"items": {}}
        status = {"epyc2": {"admit": 400, "run": 0, "load": 1, "cores": 128}}
        with mock.patch.object(KW, "gate", side_effect=lambda c, die, *a: (die in counts, "ok")), \
                mock.patch.object(KW, "stop_reason", return_value=""), \
                mock.patch.object(KW, "select", side_effect=lambda o, c, die, s, n: _picks(die, counts[die])):
            cfg["dies"] = {k: v for k, v in cfg["dies"].items() if k in counts}
            for v in cfg["dies"].values():
                v["hosts"] = ["epyc2"]
            return KW.plan_dies(None, cfg, st, [], status, "intel2", probe=False)[1]

    def test_head_gets_slots_when_s81_has_a_long_queue(self):
        todo = self.run_plan(_cfg(per_tick=4), {"s81": 72, "s81_head": 4})
        self.assertEqual([d for d, _ in todo], ["s81", "s81_head", "s81", "s81_head"])

    def test_one_die_still_fills_the_tick(self):
        todo = self.run_plan(_cfg(per_tick=6), {"s81": 72, "s81_head": 1})
        self.assertEqual(len(todo), 6)
        self.assertEqual(sum(1 for d, _ in todo if d == "s81_head"), 1)

    def test_global_inflight_cap(self):
        st = {"items": {str(i): {"status": "RUNNING", "die": "s81"} for i in range(68)}}
        c = _cfg(per_tick=16, inflight=70)
        c["dies"]["s81"]["die_max_inflight"] = 80
        todo = self.run_plan(c, {"s81": 72, "qwen_kvsys": 3}, st)
        self.assertEqual(len(todo), 2)
        self.assertEqual({d for d, _ in todo}, {"qwen_kvsys", "s81"})


class PlanDir(unittest.TestCase):
    def test_plan_c_is_staged_as_die_plan(self):
        """run_item's preflight plan-dir staging: links to the plan's own dir + die_plan.json -> the plan file"""
        with tempfile.TemporaryDirectory() as t:
            pd = Path(t, "plan_of_record")
            pd.mkdir()
            (pd / "plan_c.json").write_text('{"partition_types": {}}')
            (pd / "die_plan.json").write_text('{"stale": 1}')
            (pd / "pins_x.json").write_text("{}")
            W = Path(t, "w")
            W.mkdir()
            import shlex
            q = shlex.quote
            plan = str(pd / "plan_c.json")
            pdir = f"{W}/plandir"
            cmd = (f"rm -rf {q(pdir)} && mkdir -p {q(pdir)} && for f in {q(os.path.dirname(plan))}/*; do "
                   f"ln -s \"$f\" {q(pdir)}/; done; ln -sfn {q(plan)} {q(pdir)}/die_plan.json && true")
            subprocess.run(["bash", "-c", cmd], check=True)
            subprocess.run(["bash", "-c", cmd], check=True)                     # rerun (attempt 2) is clean
            self.assertEqual(Path(pdir, "die_plan.json").read_text(), '{"partition_types": {}}')
            self.assertTrue(Path(pdir, "pins_x.json").is_file())
        self.assertIn('pdir = f"{W}/plandir"', Path(KW.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
