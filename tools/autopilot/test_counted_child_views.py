"""KW-FIX-32: counted child views for WAIT types (record parse, outline names, candidate order, config merge)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
import abstract_detail as AD  # noqa: E402
import counted_child_views as C  # noqa: E402

REC = ("epyc2:/srv/opentallas-scratch3/claude/die-hbm-85/eco/b128_e1_resign_dq/signoff/signoff.json src c092821dbb94 "
       "flow flow-20261107-dq-hbm RE-SIGN build 85dd231f8e8d db /srv/opentallas-scratch3/claude/die-hbm-85/eco/b128_e1/"
       "run/results/asap7/hbc_ot_hbm_hc_bank128_pair_core/base/6_final.odb DESIGN-MATCH pins [pins from routed_def]")


def lef(pin_rect="10 10 10.048 10.48", pg_layer="M5", obs=("M5", "M6")):
    """one macro, one signal pin on M5, one PG pin, blanket OBS on the given layers"""
    body = "".join(f"    LAYER {l} ;\n      RECT 0 0 100 100 ;\n" for l in obs)
    return ("MACRO m\n  SIZE 100 BY 100 ;\n"
            f"  PIN ck\n    DIRECTION INPUT ;\n    PORT\n      LAYER M5 ;\n        RECT {pin_rect} ;\n    END\n  END ck\n"
            f"  PIN VDD\n    USE POWER ;\n    PORT\n      LAYER {pg_layer} ;\n        RECT 0 0 1 100 ;\n    END\n  END VDD\n"
            f"  OBS\n{body}  END\nEND m\n").splitlines(keepends=True)


class DetailPlan(unittest.TestCase):
    def test_enclosed_centre_pin_above_pg_takes_exact_shapes(self):
        p = AD.export_plan(lef())
        self.assertEqual((p["needed"], p["layers"], p["bloat_factor"], p["pg_layer"], p["enclosed"]),
                         (True, ["M6"], 0, False, ["ck"]))

    def test_pg_on_top_obs_layer_takes_the_bloat_one_form(self):
        p = AD.export_plan(lef(pg_layer="M6"))
        self.assertEqual((p["needed"], p["layers"], p["bloat_factor"], p["pg_layer"]), (True, ["M6"], 1, True))

    def test_edge_pin_or_open_layer_above_needs_nothing(self):
        self.assertFalse(AD.export_plan(lef(pin_rect="0 10 0.048 10.48"))["needed"])
        self.assertFalse(AD.export_plan(lef(obs=("M5",)))["needed"])

    def test_open_own_layer_but_blocked_above_takes_exact_shapes(self):
        # hcol_h0_ra clk (DRT-0073 11-10): M5 free around the pin, bloated M6 over it -> no via landing, not enclosed
        base = lef(obs=("M6",))
        self.assertEqual(AD.enclosed_signal_pins(base), {})
        p = AD.export_plan(base)
        self.assertEqual((p["needed"], p["layers"], p["bloat_factor"], p["pin_window"]["pins"]),
                         (True, ["M6"], 0, ["ck"]))

    def test_pin_below_the_replaced_layers_is_not_claimed_fixable(self):
        self.assertFalse(AD.export_plan(lef(pg_layer="M6", obs=("M5", "M6", "M7")))["needed"])


class ExportDetail(unittest.TestCase):
    P = dict(host="epyc2", kit="/k", base="/k/base", signoff="/k/s.json")

    def fake(self, plan, rc=0):
        calls = []

        def run(argv, timeout=600, tries=4):
            cmd = argv[-1]
            if argv[0] == "rsync":
                return 0, "", ""
            calls.append(cmd)
            if " plan --base " in cmd:
                return 0, json.dumps(plan), ""
            if "docker" not in cmd:
                return 0, "", ""
            return rc, "", "boom" if rc else ""
        return run, calls

    def go(self, plan, rc=0, on_hub=False):
        run, calls = self.fake(plan, rc)
        logs, orig = [], C.run
        C.run = run
        try:
            out = C.view_detail("hbm", "r1", self.P, "m", "/v/m", on_hub, logs.append)
        finally:
            C.run = orig
        return out, calls, logs

    def test_needed_exports_the_wave_candidate_fields(self):
        out, calls, _ = self.go(dict(needed=True, layers=["M6"], bloat_factor=0, pg_layer=False, enclosed=["ck"]))
        self.assertEqual(out, dict(detailed_lef="detail_view.lef", detailed_receipt="detail_receipt.json",
                                   detail_bloat_factor=0))
        work = next(c for c in calls if "docker" in c)
        self.assertIn("--bloat-factor 0", work)
        self.assertIn("--layers M6", work)
        self.assertIn("realpath /k/base/6_final.odb", work)

    def test_pin_window_exports_exact_shapes_and_passes_the_window(self):
        pw = dict(margin_um=1.0, top_layer="M7", clear_um=0.05, pins=["ck"])
        _, calls, logs = self.go(dict(needed=True, layers=["M6", "M7"], bloat_factor=1, enclosed=["ck"], pin_window=pw))
        work = next(c for c in calls if "docker" in c)
        self.assertIn("write_abstract_lef -bloat_factor 0 /o/detail0.lef", work)
        self.assertIn("--pin-window-um 1.0 --top-layer M7 --window-detail $T/detail0.lef", work)
        self.assertTrue(any("pin windows ['ck']" in x for x in logs))
        _, calls, _ = self.go(dict(needed=True, layers=["M6"], bloat_factor=0, enclosed=["ck"], pin_window=pw))
        work = next(c for c in calls if "docker" in c)
        self.assertNotIn("detail0.lef", work)                     # bloat 0: the detail itself is the exact export
        self.assertIn("--window-detail $T/detail.lef", work)

    def test_real_plan_of_a_blanket_centre_pin_asks_for_the_window(self):
        p = AD.export_plan(lef(obs=("M5", "M6", "M7")))
        self.assertEqual(p["pin_window"]["pins"], ["ck"])
        self.assertEqual(p["pin_window"]["top_layer"], "M7")

    def test_pg_form_opts_in_explicitly(self):
        out, _, _ = self.go(dict(needed=True, layers=["M6"], bloat_factor=1, pg_layer=True, enclosed=["ck"]))
        self.assertIs(out["detail_pg_layer"], True)
        self.assertEqual(out["detail_bloat_factor"], 1)

    def test_not_needed_runs_nothing_more(self):
        out, calls, _ = self.go(dict(needed=False))
        self.assertEqual(out, {})
        self.assertFalse(any("docker" in c for c in calls))

    def test_failure_keeps_the_export_and_logs(self):
        out, _, logs = self.go(dict(needed=True, layers=["M6"], bloat_factor=0, enclosed=["ck"]), rc=3)
        self.assertEqual(out, {})
        self.assertTrue(any(x.startswith("DETAIL-FAIL") for x in logs))

    def test_hub_record_is_flagged_not_built(self):
        out, calls, logs = self.go(dict(needed=True, layers=["M6"], bloat_factor=0, enclosed=["ck"]), on_hub=True)
        self.assertEqual(out, {})
        self.assertFalse(any("docker" in c for c in calls))
        self.assertTrue(any(x.startswith("DETAIL-NEEDED-ON-HUB") for x in logs))


class Names(unittest.TestCase):
    def test_outline_variant_names(self):
        self.assertEqual(C.norm_module("ot_hbm_hc_bank128_pair_core#250.56x267.84/10ac9d744407ff50"),
                         "ot_hbm_hc_bank128_pair_core")
        self.assertEqual(C.norm_module("ot_hbm_idx_tail_native__v9496b22d4b49"), "ot_hbm_idx_tail_native")
        self.assertEqual(C.norm_module("hfd_ep_static"), "hfd_ep_static")
        self.assertEqual(C.outline_of("m#250.56x267.84/10ac9d74"), ("250.56x267.84", "10ac9d74"))
        self.assertEqual(C.outline_of("m"), (None, None))

    def test_parse_record(self):
        p = C.parse_record(REC)
        self.assertEqual(p["host"], "epyc2")
        self.assertTrue(p["signoff"].endswith("b128_e1_resign_dq/signoff/signoff.json"))
        self.assertEqual(p["kit"], "/srv/opentallas-scratch3/claude/die-hbm-85/eco/b128_e1")
        self.assertTrue(p["base"].endswith("/base"))
        self.assertEqual(p["flow_tag"], "flow-20261107-dq-hbm")
        self.assertIsNone(C.parse_record("no host here"))

    def test_counter_records_all_outlines_dedup(self):
        counter = {"plans": {"a": {"die": "hbm", "signed_designs": {
            "m#1x2/aaaa": [REC], "m#3x4/bbbb": [REC.replace("b128_e1_resign_dq", "other"), REC], "x": []}}},
            "b": {"die": "qc", "signed_designs": {"m": [REC]}}}
        r = C.counter_records(counter, "hbm")
        self.assertEqual([n for n, _ in r["m"]], ["m#1x2/aaaa", "m#3x4/bbbb"])   # duplicate sign-off path dropped
        self.assertNotIn("x", r)


class Order(unittest.TestCase):
    def test_plan_pin_match_first_and_cap(self):
        cands = [dict(dir=str(i), pins_sha256=f"{i:02d}" * 32) for i in range(5)]
        out = C.order_candidates(cands, ["0303030303"])
        self.assertEqual(out[0]["dir"], "3")
        self.assertTrue(out[0]["plan_pin_match"])
        self.assertEqual(len(out), C.PROV_MAX)
        self.assertEqual([c["dir"] for c in C.order_candidates(cands[:2], [])], ["0", "1"])


class LefOnly(unittest.TestCase):
    def test_lef_only_problem_triggers_odb_abstract(self):
        m = "ot_hbm_su_pcol_s"
        self.assertTrue(C.lef_only({"problems": [f"view file {m}.lef not found in kit/views, base or signoff dir"]}, m))
        self.assertFalse(C.lef_only({"problems": [f"view file {m}.lef not found", "stale sign-off record"]}, m))
        self.assertFalse(C.lef_only({"problems": [f"view file {m}_ff.lib not found"]}, m))
        self.assertFalse(C.lef_only({"problems": []}, m))

    def test_needs_parent_verdict_only(self):
        v = "signoff.json verdict 'LOCAL_PASS_NEEDS_PARENT' is not SIGNED"
        self.assertTrue(C.needs_parent_only({"problems": [v]}))
        self.assertFalse(C.needs_parent_only({"problems": [v, "stale sign-off record"]}))
        self.assertFalse(C.needs_parent_only({"problems": ["signoff.json verdict 'FAIL' is not SIGNED"]}))
        self.assertFalse(C.needs_parent_only(None))


class Parse(unittest.TestCase):
    def test_one_line_and_indented(self):
        self.assertEqual(C.parse_result('log\n{"module": "m", "complete": true}\n')["module"], "m")
        r = C.parse_result('x {"a": 1}\n{\n "module": "m",\n "complete": false,\n "problems": ["p {q}"]\n}\n')
        self.assertFalse(r["complete"])
        self.assertIsNone(C.parse_result("no json"))


class Dedup(unittest.TestCase):
    def test_same_view_in_several_worktrees_is_one_candidate(self):
        recs = {"m": [("m", dict(host="e2", signoff=f"/w{i}/signoff.json", kit="/k", base="/b", db="/b/6_final.odb",
                                 flow_tag=None)) for i in range(3)]}
        calls = []

        def fake(die, name, p, log):
            calls.append(p["signoff"])
            return dict(host="e2", dir=p["signoff"], job="j", pins_sha256="aa", pins_canon_sha256="bb", outline=None)
        old_e, old_r, old_w = C.export_one, C.counter_records, C.wait_children
        try:
            C.export_one, C.counter_records = fake, lambda counter, die: recs
            C.wait_children = lambda state, cfg, die: ({"m": ["t"]}, {})
            man = C.build_manifest("qc", {}, {}, {}, log=lambda s: None)
        finally:
            C.export_one, C.counter_records, C.wait_children = old_e, old_r, old_w
        self.assertEqual(len(calls), 3)
        self.assertEqual([c["dir"] for c in man["modules"]["m"]["candidates"]], ["/w0/signoff.json"])


class Apply(unittest.TestCase):
    def test_merge_first_keep_prev(self):
        cfg = {"dies": {"qc": {"prov_view_sources": {"m": [{"host": "h", "dir": "/old", "job": "die owner"}]}}}}
        man = {"die": "qc", "generated": "t", "modules": {
            "m": {"candidates": [{"host": "epyc2", "dir": "/v/m", "job": "COUNTED m"}]},
            "n": {"candidates": [{"host": "epyc4", "dir": "/v/n", "job": "COUNTED n"}, {"host": "x", "dir": None}]},
            "z": {"candidates": []}}}
        ch = C.apply_manifest(cfg, man)
        d = cfg["dies"]["qc"]
        self.assertEqual(sorted(ch), ["m", "n"])
        self.assertEqual([c["dir"] for c in d["prov_view_sources"]["m"]], ["/v/m", "/old"])
        self.assertEqual([c["dir"] for c in d["prov_view_sources"]["n"]], ["/v/n"])
        self.assertEqual(d["prov_view_sources_prev_kw32"]["m"][0]["dir"], "/old")
        self.assertEqual(C.apply_manifest(cfg, man), [])            # idempotent
        self.assertEqual(d["prov_view_sources_prev_kw32"]["m"][0]["dir"], "/old")


if __name__ == "__main__":
    unittest.main()
