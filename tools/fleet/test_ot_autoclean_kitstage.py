"""KIT-STAGE-1 11-13: (1) the inputs a live kit-wave row reads are protected TRANSITIVELY (spec -> bind_out -> bind.f /
asbuilt -> sources; the die config's inputs too, rows not launched yet have no spec); (2) OWNER 11-13: every attempt keeps
its reports/ and logs/ dirs when the aggressive cleanup removes it.
    python3 -I tools/fleet/test_ot_autoclean_kitstage.py"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_ot_autoclean_auto as T   # noqa: E402
import test_ot_autoclean_live as L   # noqa: E402

ac = T.ac


class InputPaths(unittest.TestCase):
    def test_spec_input_paths_reads_every_input_field_not_notes(self):
        spec = {"src": "/srv/s/claude/kw45/src_x", "work": "/srv/s/claude/w/items/t/attempt_1",
                "kit_rtl": {"mode": "bind", "bind_out": "/srv/s/claude/lane/bind", "asbuilt": "/srv/s/claude/lane/ab.json",
                            "note": "/srv/s/claude/old/never", "prep_cmd": "python3 x --sidecar /srv/s/claude/lane/sc.json"},
                "gen_args": ["--clock-landing", "/srv/s/claude/l2/side.json"], "gen_env": {"OT_X": "/srv/s/claude/l3/y.tcl"}}
        got = ac.spec_input_paths(spec)
        for p in ("/srv/s/claude/kw45/src_x", "/srv/s/claude/lane/bind", "/srv/s/claude/lane/ab.json",
                  "/srv/s/claude/lane/sc.json", "/srv/s/claude/l2/side.json", "/srv/s/claude/l3/y.tcl"):
            self.assertIn(p, got)
        self.assertNotIn("/srv/s/claude/old/never", got)
        self.assertNotIn("/srv/s/claude/w/items/t/attempt_1", got)         # where the row runs is not an input

    def test_config_keep_enabled_dies_only_current_keys(self):
        cfg = {"enabled": True, "dies": {
            "qc": {"src": "/srv/s/claude/kw45/src_qc", "plan": "/srv/s/claude/kw45/src_qc/p.json",
                   "kit_rtl": {"bind_out": "/srv/s/claude/qcs28in/bind", "asbuilt": "/srv/s/claude/sw2/ab.json"},
                   "src_prev_kw40": "/srv/s/claude/old_src", "note_x": "/srv/s/claude/n"},
            "off": {"enabled": False, "src": "/srv/s/claude/kw45/src_off"}}}
        got = ac.config_keep(cfg)
        self.assertIn("/srv/s/claude/qcs28in/bind", got)
        self.assertIn("/srv/s/claude/sw2/ab.json", got)
        self.assertNotIn("/srv/s/claude/old_src", got)
        self.assertIn("/srv/s/claude/kw45/src_off", got)              # a wave src stays protected while its die is off

    def test_reduce_live_keeps_spec_bind_inputs_of_running_row(self):
        R = L.R
        state = {"items": {"run": L.rec("RUNNING", kit=f"e4:{R}/t1/attempt_5/gen/t1", d="/kw/run/a5")}}
        spec = {"/kw/run/a5": {"src": "/srv/s2/claude/kw45/src_qc", "kit_rtl": {"bind_out": "/srv/s2/claude/qcs28in/bind"}}}
        out = ac.reduce_live(state, [], lambda d: spec.get(d, {}), None, [], L.NOW)
        keep = {k.partition(":")[2] for k in out["live_keep"]}
        self.assertIn("/srv/s2/claude/qcs28in/bind", keep)


class Transitive(L.HostLive):
    def lane_file(self, rel, text=""):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        T.age_tree(os.path.dirname(p))
        return p

    def chain(self):
        """live row spec (hub record dir) -> bind dir -> bind.f -> source in another lane; spec -> asbuilt -> base tree"""
        src_sv = self.lane_file("hbm92-su-lane/abx/p37su_sources/core.sv", "module m; endmodule\n")
        base = os.path.join(self.root, "qc-transport-fix-4/src_sw2")
        sw2 = self.lane_file("qc-transport-fix-4/src_sw2/rtl/a.sv", "module a; endmodule\n")
        ab = self.lane_file("kit-ops-1/qc/asbuilt_x.json", json.dumps({"base": base, "files": ["rtl/a.sv"]}))
        bindf = self.lane_file("kit-ops-1/hbm/bind/bind.f", src_sv + "\n")
        junk = self.lane_file("unrelated-lane/old/x.txt", "x")
        cur = self.attempt("t1", 3)
        rdir = os.path.join(self.root, "hubrec/a3")
        os.makedirs(rdir)
        with open(os.path.join(rdir, "spec.json"), "w") as f:
            json.dump({"work": cur, "kit_rtl": {"bind_out": os.path.dirname(bindf), "asbuilt": ab}}, f)
        self.snap_kw({cur: {"active": True, "current": True}}, keep=[cur, rdir])
        T.age_tree(self.root)                     # every lane tree older than the aggressive grace
        return src_sv, sw2, bindf, junk

    def test_bind_chain_transitive_survives_aggressive_class_d(self):
        src_sv, sw2, bindf, junk = self.chain()
        self.run_job("--classes", "ad", "--live-refs-only", "--aggressive", "--d-any-root")
        self.assertTrue(os.path.exists(bindf))
        self.assertTrue(os.path.exists(src_sv), "a source the bind.f names (third level from the spec) stays")
        self.assertTrue(os.path.exists(sw2), "the asbuilt base tree stays")
        self.assertFalse(os.path.exists(junk), "an unreferenced lane tree still goes")

    def test_control_one_level_loses_the_sources(self):
        src_sv, sw2, bindf, junk = self.chain()
        old = ac.Job.BIND_DEPTH
        ac.Job.BIND_DEPTH = 1                     # the 11-12 behaviour: one level from the keep paths
        try:
            self.run_job("--classes", "ad", "--live-refs-only", "--aggressive", "--d-any-root")
        finally:
            ac.Job.BIND_DEPTH = old
        self.assertTrue(os.path.exists(bindf))
        self.assertFalse(os.path.exists(src_sv), "control: without the transitive walk the bind source is deleted")


class KeepReports(L.HostLive):
    def test_finished_attempt_keeps_reports_and_logs_once(self):
        d = self.attempt("t1", 4)
        rep = os.path.join(d, "gen/t1/run/reports/asap7/dp_t1/base/2_floorplan_final.rpt")
        log = os.path.join(d, "gen/t1/run/logs/asap7/dp_t1/base/3_3_place_gp.log")
        T.touch(rep, 100)
        T.touch(log, 100)
        T.age_tree(d)
        other = self.attempt("t1", 5)
        self.snap_kw({d: {"current": False, "history": "superseded: x"}, other: {"active": True, "current": True}},
                     keep=[other])
        self.run_job("--classes", "a", "--live-refs-only", "--aggressive")
        self.assertTrue(os.path.exists(rep))
        self.assertTrue(os.path.exists(log))
        self.assertFalse(os.path.exists(os.path.join(d, "gen/t1/run/results")), "results go")
        self.assertTrue(os.path.exists(os.path.join(d, ac.REPORTS_KEPT_MARK)))
        self.assertEqual(self.row(d)[3], "DELETED")
        self.run_job("--classes", "a", "--live-refs-only", "--aggressive")
        self.assertIn("diagnostics remainder", self.row(d)[4])

    def test_tree_without_diagnostics_removed_whole(self):
        d = self.attempt("t2", 1)
        other = self.attempt("t2", 2)
        self.snap_kw({d: {"history": "superseded: x"}, other: {"active": True, "current": True}}, keep=[other])
        self.run_job("--classes", "a", "--live-refs-only", "--aggressive")
        self.assertFalse(os.path.exists(d))


if __name__ == "__main__":
    unittest.main()
