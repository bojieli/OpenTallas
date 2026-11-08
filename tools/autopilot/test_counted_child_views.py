"""KW-FIX-32: counted child views for WAIT types (record parse, outline names, candidate order, config merge)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import counted_child_views as C  # noqa: E402

REC = ("epyc2:/srv/opentallas-scratch3/claude/die-hbm-85/eco/b128_e1_resign_dq/signoff/signoff.json src c092821dbb94 "
       "flow flow-20261107-dq-hbm RE-SIGN build 85dd231f8e8d db /srv/opentallas-scratch3/claude/die-hbm-85/eco/b128_e1/"
       "run/results/asap7/hbc_ot_hbm_hc_bank128_pair_core/base/6_final.odb DESIGN-MATCH pins [pins from routed_def]")


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
