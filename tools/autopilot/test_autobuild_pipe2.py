#!/usr/bin/env python3
"""AUTOBUILD-PIPE-2 (OWNER 12.23): round-robin launches across dies; plan files not named die_plan.json."""
import json
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


def _hbm(clock="FAIL", core_kit=True):
    d = {"enabled": True, "coord_enable": "COORD 23:5x", "event": "d44f", "plan": "/srv/p/d44f/die_plan.json",
         "gen_host": "intel2", "src": "/srv/wt/kw", "kinds": ["core", "type"],
         "gate": {"g0c": "PASS", "bind": "PASS", "clock": clock}}
    if core_kit:
        d["core_kit"] = {"item_args": {"hnx_fused_lane": ["--clock-taps", "density"]}}
    return {"enabled": True, "dies": {"hbm": d}}


OWN_HBM = [dict(die="hbm", item=i, kind=k, state="NEEDS-KIT", owner="HBM-CORES", live_job="none", last_activity="900m",
                next_step="", evidence="", default_owner="", replicas="4", members="")
           for i, k in (("hnx_fused_lane", "core"), ("hfd_ep_static", "core"), ("q_b000", "type"))]


class CoreKit(unittest.TestCase):
    def test_clock_gate_opt_out_only_for_core_kit_dies(self):
        c = _hbm()
        ok, _ = KW.gate(c, "hbm")
        self.assertTrue(ok)
        self.assertTrue(c["dies"]["hbm"]["_cores_only"])
        self.assertFalse(KW.gate(_hbm(core_kit=False), "hbm")[0])
        c = _hbm(clock="PASS")
        self.assertTrue(KW.gate(c, "hbm")[0])
        self.assertNotIn("_cores_only", c["dies"]["hbm"])
        bad = _hbm()
        bad["dies"]["hbm"]["gate"]["bind"] = "FAIL"
        self.assertFalse(KW.gate(bad, "hbm")[0])                  # only the die clock is waived for cores

    def test_cores_only_selects_cores_and_expands_pin_tables(self):
        c = _hbm()
        KW.gate(c, "hbm")
        names = KW.core_view_names({"hnx_fused_lane": "b1", "hfd_ep_static": "b2", "q_b000": "b3"},
                                   {"hfd_ep_static": ["261e40d1235d", "936f8dc7fe73"], "hnx_fused_lane": ["aaaaaaaaaaaa"]})
        self.assertEqual(sorted(names), ["hfd_ep_static__v261e40d1235d", "hfd_ep_static__v936f8dc7fe73",
                                         "hnx_fused_lane", "q_b000"])
        picks, skip = KW.select(OWN_HBM, c, "hbm", {"items": {}}, names)
        self.assertEqual(sorted(p["item"] for p in picks),
                         ["hfd_ep_static__v261e40d1235d", "hfd_ep_static__v936f8dc7fe73", "hnx_fused_lane"])
        self.assertIn("q_b000", sum(skip.values(), []))
        self.assertEqual({p.get("parent_item") for p in picks if p["item"].startswith("hfd")}, {"hfd_ep_static"})

    def test_owners_item_with_pin_sha_maps_to_its_view(self):
        c = _hbm(clock="PASS")
        KW.gate(c, "hbm")
        rows = [dict(OWN_HBM[1], item="hfd_ep_static_936f8dc7fe73")]
        names = {"hfd_ep_static__v261e40d1235d": "b", "hfd_ep_static__v936f8dc7fe73": "b"}
        picks, _ = KW.select(rows, c, "hbm", {"items": {}}, names)
        self.assertEqual([p["item"] for p in picks], ["hfd_ep_static__v936f8dc7fe73"])

    def test_spec_and_commands(self):
        c = _hbm()
        sp = KW.spec_for(c, "hbm", "hnx_fused_lane", "intel2", kind="core")
        self.assertEqual(sp["kind"], "core")
        self.assertEqual(sp["core_kit"]["args"], ["--clock-taps", "density"])
        self.assertEqual(KW.spec_for(_hbm(core_kit=False), "hbm", "q_b000", "intel2")["core_kit"], {})
        views, vcmd, gen, find, runner = KW.core_kit_cmds(sp["core_kit"], "/s", "/p/die_plan.json", "/r", "/w", "x__v0123456789ab")
        self.assertEqual(views, "/r/core_views.json")
        self.assertIn("views_b2r2.py --plan /p/die_plan.json --out /r/core_views.json", vcmd)
        self.assertIn("gen_core_kit_hbm.py --views /r/core_views.json --view \"$VIEW\" --out /w/gen --clock-taps density", gen)
        self.assertEqual(runner, "{kit}/run_kit_hbm.sh")
        self.assertEqual(KW.core_kit_cmds({"views": "/v.json"}, "/s", "/p", "/r", "/w", "m")[1], "")

    def test_view_pick_shell(self):
        with tempfile.TemporaryDirectory() as t:
            v = Path(t, "views.json")
            v.write_text(json.dumps({"view_list": [{"view": "m@0123456789ab", "module": "m"},
                                                   {"view": "m@ba9876543210", "module": "m"},
                                                   {"view": "one@111111111111", "module": "one"}]}))
            def pick(item):
                _, _, gen, _, _ = KW.core_kit_cmds({"views": str(v), "gen_cmd": "echo GEN {view}"}, "/s", "/p", t, t, item)
                return subprocess.run(["bash", "-c", gen], capture_output=True, text=True)
            self.assertIn("GEN m@ba9876543210", pick("m__vba9876543210").stdout)
            self.assertIn("GEN one@111111111111", pick("one").stdout)
            r = pick("m")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("CORE_VIEW FAIL m@*: 2 views", r.stderr)
            self.assertEqual(KW.classify("gen", r.stderr)[0], "PLAN")

    def test_no_recipe_is_plan(self):
        self.assertEqual(KW.classify("gen", "NO_RECIPE ot_hfd_coll_q3_body_core@e9fac1f891ac\not-run: RAN on intel1 (unit x): exit 1")[0], "PLAN")


if __name__ == "__main__":
    unittest.main()


class PreflightMacroPaths(unittest.TestCase):
    def test_only_macro_instance_issues_is_plan(self):
        t = ("KIT_PREFLIGHT FAIL issues 2\n  - macro_instances: placed macro head0_e0: component 'head0_e0' is neither an "
             "instance nor a generate block of module kv3_hg_v1_part (path from kv3_hg_v1_part)\n"
             "  - macro_instances: placed macro head0_e1: component 'head0_e1' is neither ...\n")
        self.assertEqual(KW.classify("preflight", t)[0], "PLAN")

    def test_mixed_issues_stay_flow(self):
        t = ("KIT_PREFLIGHT FAIL issues 2\n  - macro_instances: placed macro head0_e0: x\n"
             "  - clock_pin_geometry: clk off track\n")
        self.assertEqual(KW.classify("preflight", t)[0], "FLOW")


class ProtectSources(unittest.TestCase):
    def test_paths_and_hosts_written_once(self):
        with tempfile.TemporaryDirectory() as td:
            jd = Path(td) / "j"
            jd.mkdir()
            (jd / "spec.json").write_text(json.dumps({"src": "/srv/x/wt/old-src", "plan": "/srv/x/wt/old-src/p.json"}))
            cfg = {"hosts": ["intel1", "intel2"], "dies": {
                "s81": {"src": "/srv/x/wt/s81", "plan": "/srv/x/wt/s81/plan.json", "gen_host": "epyc2"}, "hbm": {}}}
            st = {"items": {"a": {"status": "RUN", "dir": str(jd)}, "b": {"status": "FAIL", "dir": "/nonexistent"}}}
            self.assertEqual(KW.source_paths(cfg, st, td), ["/srv/x/wt/old-src", "/srv/x/wt/old-src/p.json",
                                                           "/srv/x/wt/s81", "/srv/x/wt/s81/plan.json"])
            calls = []

            class AP:
                HUB_NAME = "intel2"
                DRY = False

                @staticmethod
                def sh(cmd, timeout=0, input=None):
                    calls.append((cmd, input))
                    return 0, "", ""

                @staticmethod
                def log(m):
                    pass
            KW.protect_sources(AP, cfg, st, td)
            self.assertEqual(len(calls), 3)                       # epyc2, intel1 via ssh; hub local
            self.assertTrue(any(c[0][0] == "bash" for c in calls))
            self.assertTrue(all("/srv/x/wt/s81\n" in c[1] for c in calls))
            KW.protect_sources(AP, cfg, st, td)
            self.assertEqual(len(calls), 3)                       # unchanged list: no rewrite
