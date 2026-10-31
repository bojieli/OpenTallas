"""METHODOLOGY 12.1c / 12.4d / 12.4e (v2, owner 10-26): die-top signal GRT on M4-M7 + leftover M8/M9 by default,
PG IR closed before signal GRT, skew gate re-run after signal GRT."""
import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_infra as DI  # noqa: E402

GRT_TCL = ("read_verilog /work/grt/route.v\nsource /work/grt/obs.tcl\nset_routing_layers -signal M4-M7\n"
           "set_global_routing_layer_adjustment M4 0.75\nset_global_routing_layer_adjustment M8 0.4\n"
           "set_global_routing_layer_adjustment M9 0.4\n"
           "global_route -congestion_iterations 50 -congestion_report_file /work/grt/congestion.rpt\n"
           "write_guides /work/grt/route.guide\n")


class GrtLayers(unittest.TestCase):
    def _run(self, td, pg_ir="PASS", **kw):
        d = Path(td)
        kit, pre, out = d / "kit", d / "pre", d / "out"
        (kit / "grt").mkdir(parents=True)
        pre.mkdir()
        (kit / "grt" / "grt.tcl").write_text(GRT_TCL)
        (kit / "grt" / "route.v").write_text("module x(); endmodule\n")
        pg = d / "pg.json"
        pg.write_text(json.dumps({"ir_verdict": pg_ir}))
        plan=d/"plan.json"; plan.write_text('{"name":"tiny"}\n')
        (pre / "preroute.json").write_text(json.dumps({"pg_file": str(pg), "plan": str(plan),
            "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest()}))
        a = SimpleNamespace(iterations=50, plan=str(plan), kit=str(kit), pre=str(pre), out=str(out), pg=None, m89=False,
                            m47_only=False, pg_ir_open_trial=False, mem=64)
        for k, v in kw.items():
            setattr(a, k, v)
        with mock.patch.object(DI, "load_plan", return_value=None), mock.patch.object(DI, "base_obs", return_value=""):
            DI.cmd_grt(a)
        return out, pg

    def test_default_opens_leftover_m8_m9(self):
        with tempfile.TemporaryDirectory() as td:
            out, _ = self._run(td)
            t = (out / "grt.tcl").read_text()
            self.assertIn("set_routing_layers -signal M4-M9", t)
            self.assertNotIn("-signal M4-M7", t)
            self.assertNotIn("M8 0.4", t)            # the pre-route obstructions are the taken capacity
            self.assertIn("set_global_routing_layer_adjustment M8 0\n", t)
            self.assertIn("12.1c", (out / "grt_meta.json").read_text())

    def test_m47_only_is_legacy_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            out, _ = self._run(td, m47_only=True)
            self.assertIn("-signal M4-M7", (out / "grt.tcl").read_text())
            self.assertIn("LEGACY", (out / "grt_meta.json").read_text())

    def test_missing_explicit_router_request_cannot_be_recorded_as_fifty(self):
        with tempfile.TemporaryDirectory() as td, mock.patch(__name__+".GRT_TCL",GRT_TCL.replace("-congestion_iterations 50 ","")):
            with self.assertRaisesRegex(ValueError,"no request recorded"):
                self._run(td)

    def test_pg_ir_must_close_before_signal_grt(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "12.4e"):
                self._run(td, pg_ir="FAIL")
        with tempfile.TemporaryDirectory() as td:
            out, _ = self._run(td, pg_ir="FAIL", pg_ir_open_trial=True)
            self.assertTrue(json.loads((out / "grt_meta.json").read_text())["trial"])

    def test_actual_route_import_is_opt_in_and_keeps_guarded_api(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, names, provisional = root/"source.odb", root/"nets.txt", root/"provisional.txt"
            source.touch()
            names.write_text("clock\nVDD\n")
            provisional.write_text("old_clock\n")
            out, _ = self._run(td, infra_odb=str(source), infra_nets=str(names),
                               infra_provisional_nets=str(provisional))
            prep, route = (out/"prepare_signal.tcl").read_text(), (out/"grt.tcl").read_text()
            self.assertIn("write_db /out/target_signal.odb", prep)
            self.assertNotIn("global_route ", prep)
            self.assertNotIn("source /pre/preroute_obs.tcl", prep)
            self.assertIn("read_db /out/combined_infra.odb", route)
            self.assertNotIn("read_verilog", route)
            self.assertIn("write_db /out/routed_signal.odb", route)
            shell = (out/"run_import_inside.sh").read_text()
            self.assertIn("--nets /out/infra_nets.txt", shell)
            self.assertIn("--provisional-nets /out/infra_provisional.txt", shell)
            self.assertIn("verify_import.py", shell)
            compile((out/"verify_import.py").read_text(), "verify_import.py", "exec")
            self.assertIn("actual_fixed_import", (out/"grt_meta.json").read_text())
            # Execute the GENERATED outer shell with a docker argv recorder;
            # bash -n alone cannot catch a backslash followed by spaces.
            import os, subprocess
            bindir = root/"bin"; bindir.mkdir()
            docker = bindir/"docker"
            docker.write_text("#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n")
            docker.chmod(0o755)
            (root/"kit/abstracts").mkdir()
            result = subprocess.run(["bash", str(out/"run_grt.sh")], text=True, capture_output=True,
                env={**os.environ, "PATH": str(bindir)+":"+os.environ["PATH"]}, check=True)
            argv = json.loads(result.stdout)
            self.assertTrue(all(arg and arg == arg.strip() for arg in argv))
            self.assertEqual(argv.count("-v"), 5)
            self.assertIn("HUID="+str(os.getuid()), argv)
            self.assertEqual(argv[-3:], ["openroad/orfs:latest", "bash", "/out/run_import_inside.sh"])


    def test_actual_import_requires_complete_pair_and_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "required together"):
                self._run(td, infra_odb="missing.odb")
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            (d/"s.odb").touch(); (d/"nets.txt").write_text("# empty\n")
            with self.assertRaisesRegex(ValueError, "nonempty"):
                self._run(td, infra_odb=str(d/"s.odb"), infra_nets=str(d/"nets.txt"))

    def test_capacity_only_never_freezes_even_with_passing_clock_and_grt(self):
        with tempfile.TemporaryDirectory() as td:
            out, _ = self._run(td)
            (out / "grt.log").write_text("Final congestion report\n M4 100 1 1.0% 0 / 0 / 0\n"
                                         " Total 100 1 1.0% 0 / 0 / 0\nEXIT 0\n")
            d = Path(td)
            clk = d / "clock"
            clk.mkdir()
            (clk / "clock_report.json").write_text(json.dumps({"corners": {
                c: {"verdict": "PASS", "related_pair_max_ps": 10} for c in ("TT", "FF")}}))
            a = SimpleNamespace(pre=str(d / "pre"), grt=[str(out)], clock=str(clk), clock_post=str(clk),
                                pg=None, sites=None, out=str(d / "report.json"))
            baseline=json.loads((d/"pre/preroute.json").read_text())
            for extra, expected in (({}, "FAIL"), ({"connected_preroutes": False}, "FAIL"),
                                    ({"connected_preroutes": True, "qualification": "CAPACITY_RESERVATION_ONLY"}, "FAIL"),
                                    ({"connected_preroutes": True, "qualification": "CONNECTED_FIXED_ROUTES"}, "NOT RUN")):
                pre = {**baseline, "tracks_taken": {"M8": {"all": 0.1}}, **extra}
                (d / "pre/preroute.json").write_text(json.dumps(pre))
                DI.cmd_report(a)
                gate = json.loads((d / "report.json").read_text())["freeze_gate"]
                self.assertTrue(gate["signal_grt0"])
                self.assertTrue(gate["clock_alone"])
                self.assertTrue(gate["clock_post_signal"])
                self.assertEqual(gate["verdict"], expected)

    def test_pg_growth_after_grt_and_post_signal_skew_gate(self):
        with tempfile.TemporaryDirectory() as td:
            out, pg = self._run(td)
            (out / "grt.log").write_text("Final congestion report\n M4 100 1 1.0% 0 / 0 / 0\n"
                                         " Total 100 1 1.0% 0 / 0 / 0\nEXIT 0\n")
            d = Path(td)
            for name, verdict in (("clk", "PASS"), ("post", "FAIL")):
                (d / name).mkdir()
                (d / name / "clock_report.json").write_text(json.dumps(
                    {"corners": {c: {"related_pair_max_ps": 70.0, "verdict": verdict} for c in ("TT", "FF")}}))
            prior=json.loads((d/"pre/preroute.json").read_text())
            (d / "pre" / "preroute.json").write_text(json.dumps({**prior,"tracks_taken": {"M8": {"all": 0.1}}}))
            a = SimpleNamespace(pre=str(d / "pre"), grt=[str(out)], clock=str(d / "clk"), clock_post=str(d / "post"),
                                pg=None, sites=None, out=str(d / "rep.json"))
            DI.cmd_report(a)
            r = json.loads((d / "rep.json").read_text())
            self.assertEqual(r["freeze_gate"]["verdict"], "FAIL")        # post-signal skew fails
            self.assertTrue(r["freeze_gate"]["signal_grt0"])
            pg.write_text(json.dumps({"ir_verdict": "PASS", "grid": "grown"}))   # PG grows after the signal GRT
            a.clock_post = str(d / "clk")
            DI.cmd_report(a)
            r = json.loads((d / "rep.json").read_text())
            self.assertFalse(r["grt"][str(out)]["pg_unchanged_since_grt"])
            self.assertFalse(r["freeze_gate"]["signal_grt0"])
            self.assertEqual(r["freeze_gate"]["verdict"], "FAIL")


class RelatedStaGate(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        d=Path(temp.name);out,_=GrtLayers()._run(temp.name)
        (out/"grt.log").write_text("Final congestion report\n M4 100 1 1.0% 0 / 0 / 0\n Total 100 1 1.0% 0 / 0 / 0\nEXIT 0\n")
        pre=json.loads((d/"pre/preroute.json").read_text())
        pre.update(connected_preroutes=True,qualification="CONNECTED_FIXED_ROUTES",tracks_taken={"M8":{"all":.1}})
        (d/"pre/preroute.json").write_text(json.dumps(pre))
        for name in ("clock","post"):
            (d/name).mkdir()
            (d/name/"clock_report.json").write_text(json.dumps({"corners":{
                c:{"verdict":"DIAGNOSTIC-FAIL","related_pair_max_ps":300} for c in ("TT","FF")}}))
        rec=dict(plan=pre["plan"],plan_sha256=pre["plan_sha256"],proof=str(d/"post"),period_ps=833,unc_setup_ps=60,unc_hold_ps=25,
                 coverage={"uncovered_bits":{}},corners={},block_model={"label":"declared-budget"})
        for corner in ("TT","FF"):
            rec["corners"][corner]=dict(basis="routed RC (fixed geometry)",classes={
                "intra":dict(pairs=2,worst_setup_slack_ps=40,worst_hold_slack_ps=13,setup_neg_pairs=0,hold_neg_pairs=0),
                "seam":dict(pairs=2,worst_setup_slack_ps=30,worst_hold_slack_ps=12,setup_neg_pairs=0,hold_neg_pairs=0),
                "intra_cross_region":dict(pairs=0),"landed":dict(pairs=0)})
        sta=d/"sta.json";sta.write_text(json.dumps(rec))
        args=SimpleNamespace(pre=str(d/"pre"),grt=[str(out)],clock=str(d/"clock"),clock_post=str(d/"post"),
                             related_sta=str(sta),pg=None,sites=None,out=str(d/"report.json"))
        return args,rec,out,pre

    def report(self,args,rec=None):
        if rec is not None:Path(args.related_sta).write_text(json.dumps(rec))
        DI.cmd_report(args)
        return json.loads(Path(args.out).read_text())

    def test_actual_sta_pass_not_skew_target_is_freeze_gate(self):
        args,rec,_out,_pre=self.fixture()
        # The other corner/check is informational; do not take a collapsed min.
        rec["corners"]["TT"]["classes"]["intra"]["worst_hold_slack_ps"]=-999
        rec["corners"]["FF"]["classes"]["intra"]["worst_setup_slack_ps"]=-999
        result=self.report(args,rec)
        self.assertEqual(result["related_sta"]["verdict"],"PASS")
        self.assertEqual(result["freeze_gate"]["verdict"],"PASS")
        self.assertEqual(result["clock"]["TT"]["verdict"],"DIAGNOSTIC-FAIL")

    def test_missing_receipt_is_explicitly_not_run(self):
        args,_,_,_=self.fixture();args.related_sta=None
        result=self.report(args)
        self.assertEqual(result["freeze_gate"]["verdict"],"NOT RUN")
        self.assertEqual(result["related_sta"]["verdict"],"NOT RUN")

    def test_negative_actual_hold_cannot_use_positive_summary_or_hb4_model(self):
        args,rec,_,_=self.fixture()
        rec["summary"]={"seam":{"verdict":"PASS","hb4":{"ff_hold_ps":100}}}
        rec["corners"]["FF"]["classes"]["seam"].update(worst_hold_slack_ps=-1,hold_neg_pairs=1)
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"FAIL")

    def test_rounded_zero_with_negative_pair_still_fails(self):
        args,rec,_,_=self.fixture()
        rec["corners"]["TT"]["classes"]["intra"].update(worst_setup_slack_ps=0,setup_neg_pairs=1)
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"FAIL")

    def test_mismatched_or_changed_plan_fails(self):
        args,rec,_,pre=self.fixture();rec["plan_sha256"]="f"*64
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"FAIL")
        rec["plan_sha256"]=pre["plan_sha256"];Path(pre["plan"]).write_text('{"name":"changed"}')
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"FAIL")

    def test_legacy_path_without_plan_hash_is_unqualified(self):
        args,rec,_,_=self.fixture();rec.pop("plan_sha256")
        self.assertEqual(self.report(args,rec)["related_sta"]["verdict"],"NOT RUN")

    def test_partial_or_unrouted_receipt_is_unqualified(self):
        args,rec,_,_=self.fixture();rec["corners"]["FF"]["basis"]="placement estimate"
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"NOT RUN")
        rec["corners"].pop("FF")
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"NOT RUN")

    def test_pre_signal_clock_receipt_cannot_replace_post_signal_timing(self):
        args,rec,_,_=self.fixture();rec["proof"]=args.clock
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"FAIL")

    def test_uncertainty_is_not_relaxed(self):
        args,rec,_,_=self.fixture();rec["unc_hold_ps"]=0
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"FAIL")

    def test_requested_five_iteration_zero_overflow_diagnostic_does_not_freeze(self):
        args,rec,out,_=self.fixture();path=out/"grt_meta.json";meta=json.loads(path.read_text())
        meta["congestion_iterations_requested"]=5;path.write_text(json.dumps(meta))
        result=self.report(args,rec)
        self.assertEqual(result["grt"][str(out)]["verdict"],"PASS")
        self.assertFalse(result["freeze_gate"]["signal_grt0"])
        self.assertEqual(result["freeze_gate"]["verdict"],"NOT RUN")

    def test_missing_iteration_request_is_not_inferred_from_log(self):
        args,rec,out,_=self.fixture();path=out/"grt_meta.json";meta=json.loads(path.read_text())
        meta.pop("congestion_iterations_requested");path.write_text(json.dumps(meta))
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"NOT RUN")

    def test_landed_uses_existing_landing_margins_and_info_subset_does_not_gate(self):
        args,rec,_,_=self.fixture()
        for corner in ("TT","FF"):
            rec["corners"][corner]["classes"]["landed"]=dict(pairs=1,worst_setup_slack_ps=-1000,
                worst_hold_slack_ps=-1000,plan_landing=dict(setup_margin_ps=5,hold_margin_ps=3,verdict="PASS"))
            rec["corners"][corner]["classes"]["seam_nearest_INFO"]=dict(pairs=1,worst_setup_slack_ps=-1000)
        self.assertEqual(self.report(args,rec)["freeze_gate"]["verdict"],"PASS")


if __name__ == "__main__":
    unittest.main()
