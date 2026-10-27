import json
import tempfile
import unittest
from pathlib import Path

from signoff_chain import continue_kit


class ChainTest(unittest.TestCase):
    def vehicle(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        k = Path(t.name)
        b = k / "run/results/asap7/core/base"
        b.mkdir(parents=True)
        for n in ("6_final.odb", "6_final.spef", "6_final.v"):
            (b / n).touch()
        (k / "lec.py").touch()
        (k / "signoff.py").touch()
        return k, b

    def runner(self, k, b, verdict="EQUIVALENT", route_record=True):
        calls = []
        def run(cmd):
            calls.append(cmd)
            if cmd[0] == "bash" and route_record:
                p = k / "signoff/signoff.json"
                p.parent.mkdir()
                p.write_text(json.dumps({"verdict": "SIGNED", "inputs": {"base": str(b)}}))
            elif "run" in cmd and "--base" in cmd:
                p = Path(cmd[cmd.index("--out") + 1]) / "signoff.json"
                p.parent.mkdir()
                p.write_text(json.dumps({"verdict": "SIGNED", "inputs": {"base": str(b)}}))
            elif "--netlist" in cmd:
                p = Path(cmd[cmd.index("--out") + 1]) / "lec.json"
                p.parent.mkdir()
                p.write_text(json.dumps({"verdict": verdict}))
            return 0
        return run, calls

    def test_route_then_routed_lec(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b)
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, run), 0)
        self.assertEqual(calls[-1][calls[-1].index("--netlist") + 1], str(b / "6_final.v"))
        self.assertEqual(json.loads((k / "autopilot_chain.json").read_text())["verdict"], "PASS")

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
        self.assertEqual(json.loads((k / "autopilot_chain.json").read_text())["verdict"], "LEC_FAIL")

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
                                      lambda c: calls.append(c) or 0), 0)
        self.assertEqual(len(calls), 1)
        self.assertFalse((k / "autopilot_chain.json").exists())

    def test_preflight_failure_never_enters_physical_runner(self):
        k, _ = self.vehicle()
        (k / "kit_preflight.py").touch()
        calls = []
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8,
                                      lambda c: calls.append(c) or 5), 5)
        self.assertEqual(len(calls), 1)
        self.assertNotEqual(calls[0][0], "bash")

    def test_provisional_signoff_exit_one_gets_lec_without_publication(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b)
        def pending(cmd):
            result = run(cmd)
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

    def test_missing_explicit_shared_preflight_stops_before_runner(self):
        k, _ = self.vehicle()
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8,
                                      lambda c: self.fail("runner must not start"),
                                      preflight=k / "shared/kit_preflight.py"), 3)

    def test_runner_failure_preserved(self):
        k, _ = self.vehicle()
        self.assertEqual(continue_kit(k, "runner.sh", "route", 48, 8, lambda c: 17), 17)


if __name__ == "__main__":
    unittest.main()
