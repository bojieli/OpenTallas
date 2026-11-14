import json
import os
import tempfile
import unittest
from pathlib import Path

from signoff_chain import continue_kit
import pytest  # noqa: E402

@pytest.fixture(autouse=True)
def _legacy_signoff_profile(monkeypatch):
    """this module pins the pre-R-MINIMAL gates (OT_SIGNOFF_PROFILE=legacy); R-MINIMAL is covered by
    tools/die_plan/test_signoff_profile.py"""
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")


class ChainTest(unittest.TestCase):
    def vehicle(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        k = Path(t.name)
        b = k / "run/results/asap7/core/base"
        b.mkdir(parents=True)
        for n in ("6_final.odb", "6_final.spef", "6_final.v"):
            (b / n).touch()
            os.utime(b / n, (1e9, 1e9))
        (k / "lec.py").touch()
        (k / "signoff.py").touch()
        return k, b

    def runner(self, k, b, verdict="EQUIVALENT", route_record=True, all_shown=True, gates=None):
        calls = []
        checks = {g: {"verdict": "PASS"} for g in ("setup_tt", "hold_ff", "drv", "clock", "drc", "antenna", "pg")}
        checks.update(gates or {})
        def run(cmd, **kw):
            calls.append(cmd)
            if cmd[0] == "bash" and route_record:
                p = k / "signoff/signoff.json"
                p.parent.mkdir()
                p.write_text(json.dumps({"verdict": "SIGNED", "inputs": {"base": str(b)}, "checks": checks}))
            elif "run" in cmd and "--base" in cmd:
                p = Path(cmd[cmd.index("--out") + 1]) / "signoff.json"
                p.parent.mkdir()
                p.write_text(json.dumps({"verdict": "SIGNED", "inputs": {"base": str(b)}, "checks": checks}))
            elif "--netlist" in cmd:
                p = Path(cmd[cmd.index("--out") + 1]) / "lec.json"
                p.parent.mkdir()
                p.write_text(json.dumps({"verdict": verdict, "superset_vec": {"all_shown": all_shown}}))
                (p.parent / "lec.log").write_text("log")
                self.lec_env = kw.get("env", {})
            return 0
        return run, calls

    def test_route_then_routed_lec(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b)
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, run), 0)
        self.assertEqual(calls[-1][calls[-1].index("--netlist") + 1], str(b / "6_final.v"))
        self.assertEqual(json.loads(max(k.glob("autopilot_chain*.json")).read_text())["verdict"], "PASS")

    def test_missing_signoff_continues_without_reroute(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b, route_record=False)
        self.assertEqual(continue_kit(k, "runner.sh", "finish", 48, 8, run), 0)
        self.assertEqual(len([c for c in calls if c[0] == "bash"]), 1)
        self.assertEqual(len(calls), 3)

    def test_mutant_exit_zero_with_failed_lec_cannot_pass(self):
        k, b = self.vehicle()
        run, _ = self.runner(k, b, verdict="NOT EQUIVALENT")
        self.assertNotEqual(continue_kit(k, "runner.sh", "route", 48, 8, run), 0)
        self.assertEqual(json.loads(max(k.glob("autopilot_chain*.json")).read_text())["verdict"], "LEC_FAIL")

    def test_synth_netlist_cannot_replace_missing_route_netlist(self):
        k, b = self.vehicle()
        (b / "6_final.v").unlink()
        (b / "1_2_yosys.v").touch()
        run, calls = self.runner(k, b)
        self.assertNotEqual(continue_kit(k, "runner.sh", "route", 48, 8, run), 0)
        self.assertEqual(len(calls), 1)

    def test_diagnostic_never_continues(self):
        k, _ = self.vehicle()
        calls = []
        self.assertEqual(continue_kit(k, "runner.sh", "grt", 48, 8,
                                      lambda c, **kw: calls.append(c) or 0), 0)
        self.assertEqual(len(calls), 1)
        self.assertFalse((k / "autopilot_chain.json").exists())

    def test_preflight_failure_never_enters_physical_runner(self):
        k, _ = self.vehicle()
        (k / "kit_preflight.py").touch()
        calls = []
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8,
                                      lambda c, **kw: calls.append(c) or 5), 5)
        self.assertEqual(len(calls), 1)
        self.assertNotEqual(calls[0][0], "bash")

    def test_provisional_signoff_exit_one_gets_lec_without_publication(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b)
        def pending(cmd, **kw):
            result = run(cmd, **kw)
            if cmd[0] == "bash":
                p = k / "signoff/signoff.json"
                rec = json.loads(p.read_text())
                rec["verdict"] = "LOCAL_PASS_NEEDS_PARENT"
                p.write_text(json.dumps(rec))
                return 1
            return result
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, pending), 0)
        rec = json.loads((k / "signoff/signoff.json").read_text())
        self.assertEqual(rec["verdict"], "LOCAL_PASS_NEEDS_PARENT")
        self.assertIn("--netlist", calls[-1])

    def test_external_preflight_covers_kit_without_copying_tools(self):
        k, b = self.vehicle()
        source = k / "shared/kit_preflight.py"
        source.parent.mkdir()
        source.touch()
        run, calls = self.runner(k, b)
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, run,
                                      preflight=source), 0)
        self.assertEqual(calls[0][1], str(source))
        self.assertFalse((k / "kit_preflight.py").exists())

    def test_planless_preflight_keeps_gen_time_verdict_and_plan_dir_passes(self):
        # KW-FIX-44 11-10 (DIE-KV-97): the run's plan-less preflight overwrote KIT/preflight.json (macro_pin_grid
        # 'no plan contents (pass --plan-dir)'); it now keeps the gen-time verdict, and a given plan dir is passed on
        k, b = self.vehicle()
        source = k / "shared/kit_preflight.py"
        source.parent.mkdir()
        source.write_text("ap.add_argument('--no-emit')\nap.add_argument('--plan-dir')\n")
        (k / "preflight.json").write_text("{}")
        run, calls = self.runner(k, b)
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, run, preflight=source), 0)
        self.assertIn("--no-emit", calls[0])
        self.assertNotIn("--plan-dir", calls[0])
        k2, b2 = self.vehicle()
        run2, calls2 = self.runner(k2, b2)
        self.assertEqual(continue_kit(k2, "runner.sh", "route", 48, 8, run2, preflight=source, plan_dir="/p/plandir"), 0)
        self.assertEqual(calls2[0][calls2[0].index("--plan-dir") + 1], "/p/plandir")
        self.assertNotIn("--no-emit", calls2[0])
        # an old staged preflight without --no-emit is called as before (no unknown flag)
        old = k / "shared/old_preflight.py"
        old.write_text("ap.add_argument('--out')\n")
        run3, calls3 = self.runner(*self.vehicle())
        self.assertEqual(continue_kit(k, "runner.sh", "grt", 48, 8, run3, preflight=old), 0)
        self.assertNotIn("--no-emit", calls3[0])

    def test_missing_explicit_shared_preflight_stops_before_runner(self):
        k, _ = self.vehicle()
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8,
                                      lambda c, **kw: self.fail("runner must not start"),
                                      preflight=k / "shared/kit_preflight.py"), 3)

    def test_proof_oom_can_resume_without_rerouting_or_overwriting_failure(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b)
        def oom(cmd, **kw):
            if "--netlist" in cmd:
                return 137
            return run(cmd, **kw)
        self.assertEqual(continue_kit(k, "runner.sh", "route", 24, 8, oom), 137)
        old = max(k.glob("autopilot_chain*.json"))
        old_text = old.read_text()
        self.assertEqual(json.loads(old_text)["verdict"], "LEC_OOM")
        calls.clear()
        self.assertEqual(continue_kit(k, "runner.sh", "route", 300, 8, run, proof_only=True), 0)
        self.assertFalse(any(cmd[0] == "bash" for cmd in calls))
        self.assertEqual(old.read_text(), old_text)
        self.assertEqual(len(list(k.glob("autopilot_chain*.json"))), 2)

    def test_runner_failure_preserved(self):
        k, _ = self.vehicle()
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, lambda c, **kw: 17), 17)

    def test_main_lec_tool_used_with_superset_check(self):
        k, b = self.vehicle()
        tool = k / "bundle/lec.py"
        tool.parent.mkdir()
        tool.touch()
        run, calls = self.runner(k, b)
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, run, lec=tool), 0)
        self.assertEqual(calls[-1][1], str(tool))
        self.assertEqual(self.lec_env.get("OT_LEC_SUPERSET_VEC"), "1")
        rec = json.loads(max(k.glob("autopilot_chain*.json")).read_text())
        self.assertEqual(rec["gates"]["routed_lec"], "PASS")

    def test_equivalent_without_all_shown_fails(self):
        k, b = self.vehicle()
        run, _ = self.runner(k, b, all_shown=False)
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, run), 1)
        self.assertEqual(json.loads(max(k.glob("autopilot_chain*.json")).read_text())["verdict"], "LEC_FAIL")

    def test_proof_not_newer_than_route_fails(self):
        k, b = self.vehicle()
        run, _ = self.runner(k, b)
        def stale(cmd, **kw):
            r = run(cmd, **kw)
            if "--netlist" in cmd:
                out = Path(cmd[cmd.index("--out") + 1])
                for n in ("lec.json", "lec.log"):
                    os.utime(out / n, (1e8, 1e8))
            return r
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, stale), 1)
        rec = json.loads(max(k.glob("autopilot_chain*.json")).read_text())
        self.assertIn("stale", rec["reason"])

    def test_signed_record_missing_gate_is_not_signed(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b, gates={"pg": {"verdict": "NOT RUN"}, "drv": None})
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, run), 1)
        rec = json.loads(max(k.glob("autopilot_chain*.json")).read_text())
        self.assertEqual(rec["verdict"], "NOT_SIGNED")
        self.assertIn("pg=NOT RUN", rec["reason"])
        self.assertFalse(any("--netlist" in c for c in calls))


class LateEcoTest(unittest.TestCase):
    """KW-ECO-1: a NOT SIGNED TIMING/DRV route goes through the late-stage ECO loop before any FAIL"""

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.k = k = Path(t.name)
        self.b = k / "run/results/asap7/core/base"
        self.eb = k / "eco_1/i1/run/results/asap7/core/base"
        for b in (self.b, self.eb):
            b.mkdir(parents=True)
            for n in ("6_final.odb", "6_final.spef", "6_final.v"):
                (b / n).touch()
                os.utime(b / n, (1e9, 1e9))
        (k / "lec.py").touch()
        self.calls = []

    def fake(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd[0] == "bash":
            p = self.k / "signoff/signoff.json"
            p.parent.mkdir()
            p.write_text(json.dumps({"verdict": "NOT SIGNED", "inputs": {"base": str(self.b)},
                                     "checks": {"hold_ff": {"verdict": "FAIL", "wns_ps": -3.0}}}))
            return 1
        if "--netlist" in cmd:
            p = Path(cmd[cmd.index("--out") + 1]) / "lec.json"
            p.parent.mkdir()
            p.write_text(json.dumps({"verdict": "EQUIVALENT", "superset_vec": {"all_shown": True}}))
            (p.parent / "lec.log").write_text("log")
        return 0

    def eco(self, verdict):
        def loop(kit, record, runner, mem, threads, run=None):
            self.eco_called = (kit, record, runner)
            res = {"verdict": verdict, "reason": "r", "kind": "eco", "root": str(self.k / "eco_1"),
                   "base_routed_db": str(self.b / "6_final.odb"), "iterations": [{"n": 1, "metrics": {}}],
                   "summary": ("late-ECO PASS" if verdict == "PASS" else "late-ECO exhausted (1 it)")}
            if verdict == "PASS":
                so = self.k / "eco_1/i1/signoff/signoff.json"
                so.parent.mkdir(parents=True)
                checks = {g: {"verdict": "PASS"} for g in ("setup_tt", "hold_ff", "drv", "clock", "drc", "antenna", "pg")}
                so.write_text(json.dumps({"verdict": "SIGNED", "inputs": {"base": str(self.eb)}, "checks": checks}))
                res["best"] = {"n": 1, "signoff": str(so), "base": str(self.eb)}
            return res
        return loop

    def receipt(self):
        return json.loads(max(self.k.glob("autopilot_chain*.json")).read_text())

    def test_eco_pass_goes_to_routed_lec_on_eco_netlist(self):
        self.assertEqual(continue_kit(self.k, "runner.sh", "route", 48, 8, self.fake, eco_loop=self.eco("PASS")), 0)
        r = self.receipt()
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["eco"]["verdict"], "PASS")
        self.assertEqual(self.calls[-1][self.calls[-1].index("--netlist") + 1], str(self.eb / "6_final.v"))
        link = Path(r["eco"]["signoff_link"])
        self.assertTrue(link.is_symlink() and link.name.startswith("signoff_eco_"))
        self.assertEqual(r["signoff"], str(link / "signoff.json"))   # the autopilot probe reads the ECO record
        self.assertEqual(self.eco_called[2], "runner.sh")

    def test_eco_exhausted_keeps_fail_path_with_evidence(self):
        self.assertEqual(continue_kit(self.k, "runner.sh", "route", 48, 8, self.fake, eco_loop=self.eco("EXHAUSTED")), 1)
        r = self.receipt()
        self.assertEqual(r["verdict"], "RUNNER_FAIL")
        self.assertIn("late-ECO exhausted", r["reason"])
        self.assertFalse(any("--netlist" in c for c in self.calls))
        self.assertFalse(list(self.k.glob("signoff_eco_*")))

    def test_opt_outs(self):
        def boom(*a, **kw):
            raise AssertionError("ECO must not run")
        self.assertEqual(continue_kit(self.k, "runner.sh", "route", 48, 8, self.fake, late=False, eco_loop=boom), 1)
        self.assertNotIn("eco", self.receipt())
        (self.k / "signoff/signoff.json").unlink()
        (self.k / "signoff").rmdir()
        (self.k / "late_eco.off").touch()
        self.assertEqual(continue_kit(self.k, "runner.sh", "route", 48, 8, self.fake, eco_loop=boom), 1)

    def test_runner_crash_is_not_an_eco_case(self):
        def crash(cmd, **kw):
            r = self.fake(cmd, **kw)
            return 7 if cmd[0] == "bash" else r
        def boom(*a, **kw):
            raise AssertionError("ECO must not run")
        self.assertEqual(continue_kit(self.k, "runner.sh", "route", 48, 8, crash, eco_loop=boom), 7)


if __name__ == "__main__":
    unittest.main()
