"""tools/geom_attendance.py: UNATTENDED = failure + no live job + no review in flight + no action in < 2 h."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="geomatt_")
os.environ["GEOM_REVIEW_LANE"] = _TMP + "/GEOM-REVIEW.md"
os.environ["GEOM_REVIEW_DIR"] = _TMP + "/verdicts"
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import geom_attendance as A  # noqa: E402

A.G.LANE = Path(_TMP + "/GEOM-REVIEW.md")

OLD = time.time() - 5 * 3600


def row(e, cat="needs redesign (no live job)", failed=1, live=0, design="hbm"):
    return {"element": e, "category": cat, "failed": failed, "live": live, "owner": "X",
            "dies": [{"design": design}], "latest": {"t": OLD, "status": "NEEDS_RTL", "job": e + "-j"}}


class Attendance(unittest.TestCase):
    def build(self, rows, cmap=None, lidx=None, lane="", lanes=(), ps=""):
        return {r["element"]: r for r in A.build(rows, cmap or {}, lidx or {}, [], lane, [], list(lanes), ps)}

    def test_unattended_and_attended(self):
        r = self.build([row("ot_hbm_a")])
        self.assertTrue(r["ot_hbm_a"]["unattended"])
        self.assertIn("STEWARD-HBM", r["ot_hbm_a"]["owner"])
        # live loop job -> attended
        r = self.build([row("ot_hbm_a")], lidx={"ot_hbm_a": [{"name": "j", "status": "RUNNING", "t": OLD, "kit": None,
                                                            "reason": ""}]})
        self.assertFalse(r["ot_hbm_a"]["unattended"])
        # review requested -> attended
        r = self.build([row("ot_hbm_a")], lane="- REQ ot_hbm_a physical/ref_tile/k@abc p.png s.json AG\n")
        self.assertEqual(r["ot_hbm_a"]["review"], "requested")
        self.assertFalse(r["ot_hbm_a"]["unattended"])
        # FAIL verdict after the REQ and nothing since -> back to unattended once idle
        lane = ("- REQ ot_hbm_a physical/ref_tile/k@abc p.png s.json AG\n"
                "- VERDICT ot_hbm_a physical/ref_tile/k@abc FAIL hash=0123456789abcdef low fill\n")
        r = self.build([row("ot_hbm_a")], lane=lane)
        self.assertEqual(r["ot_hbm_a"]["review"], "FAIL")
        # ot-run gate process naming its kit -> live
        r = self.build([row("ot_hbm_a")], cmap={"ot_hbm_a": [("ot_hbm_a__kk1", "BAD", "x")]},
                       ps="python3 ot-run --mem 32 -- bash /tmp/ref_gate_kk1_20261023-002223.sh\n")
        self.assertEqual(r["ot_hbm_a"]["live"], "y")
        # a lane touched recently with the element in its tail -> recent action
        r = self.build([row("ot_hbm_a")], lanes=[("L", time.time(), ["- [AG 01:00] ot_hbm_a NEXT: redesign"])])
        self.assertFalse(r["ot_hbm_a"]["unattended"])
        self.assertIn("AG", r["ot_hbm_a"]["owner"])

    def test_geom_fail_without_viz_row(self):
        lane = "- VERDICT s81_g3_col_h10_r1__t1 physical/die_plan/s81@abc FAIL hash=0123456789abcdef gap [01-01 00:00]\n"
        r = self.build([], lane=lane)
        self.assertIn("s81_g3_col_h10_r1__t1", r)
        self.assertTrue(r["s81_g3_col_h10_r1__t1"]["failure"].startswith("GEOM FAIL"))
        self.assertTrue(r["s81_g3_col_h10_r1__t1"]["unattended"])
        # a re-REQ after the FAIL -> attended; a later PASS drops it from the audit
        r = self.build([], lane=lane + "REQ s81_g3_col_h10_r1__t1 physical/die_plan/s81@def p.png s.json S81\n")
        self.assertFalse(r["s81_g3_col_h10_r1__t1"]["unattended"])
        r = self.build([], lane=lane + "- VERDICT s81_g3_col_h10_r1__t1 physical/die_plan/s81@def PASS hash=1 ok\n")
        self.assertNotIn("s81_g3_col_h10_r1__t1", r)
        # the owner lane names the kit, not the element -> counts as an action
        r = self.build([], lane=lane, lanes=[("L", time.time(), ["- [S81-P8 01:00] col_h10_r1__t1 re-space running"])])
        self.assertFalse(r["s81_g3_col_h10_r1__t1"]["unattended"])

    def test_verdict_kit_field_with_spaces(self):
        lane = ("REQ s81_g3_col_h9_r2__t1 physical/die_plan/s81@abc p.png s.json S81\n"
                "- VERDICT s81_g3_col_h9_r2__t1 physical/die_plan/s81@abc kit ot-epyc9:/srv/k/col_h9_r2__t1 FAIL "
                "hash=0123456789abcdef gap\n")
        r = self.build([], lane=lane)
        self.assertEqual(r["s81_g3_col_h9_r2__t1"]["review"], "FAIL")

    def test_scope(self):
        r = self.build([row("closed_one", cat="closed (TT era)"), row("other_die", design="old"),
                        row("qfd_bad", cat="closed (TT era)", failed=0)],
                       cmap={"qfd_bad": [("qfd_bad__k", "BAD", "x")], "qfd_new": [("qfd_new__k", "BAD", "y")]})
        self.assertNotIn("closed_one", r)
        self.assertNotIn("other_die", r)
        self.assertNotIn("qfd_bad", r)          # COORD BAD but closed since
        self.assertIn("qfd_new", r)             # COORD BAD top without a viz row
        self.assertTrue(r["qfd_new"]["coord_bad"])
        self.assertEqual([x["element"] for x in A.awaiting(r.values())], ["qfd_new"])


    def test_superseded(self):
        rows = [row("qfd_coll_face_s0_cxb", design="qwen_compute"), row("qkd_hr_ingest_eng_sp6", design="qwen_kvsys"),
                row("qkd_kvs_emb_rope_ovl", design="qwen_kvsys"), row("qkd_kvs_emb_ctx", design="qwen_kvsys"),
                row("ot_hbm_keep")]
        lane = "- SUPERSEDED qfd_coll_face_s0_cxb by qfd_collective_static_io_production (COORD)\n"
        tree = ["  - [ ] K.STA.HOST ingest_qm · STEWARD-QKd · WAITS · NEXT: sp6/sp7f/sp7g + hr_cluster_e p10a SUPERSEDED/off-die",
                "  - [ ] K.STA.EMB kvs_emb · QTILE-R · REVIEW · NEXT: nc32 kit; rope_ovl/rope73_c7m SUPERSEDED/off-die",
                "  - [ ] H.GRT.IR · STEWARD · WAITS · ot_hbm_keep r18h2 stopped (superseded) · NEXT: ir"]
        r = {x["element"]: x for x in A.build(rows, {}, {}, [], lane, tree, [], "")}
        self.assertNotIn("qfd_coll_face_s0_cxb", r)
        self.assertNotIn("qkd_hr_ingest_eng_sp6", r)
        self.assertNotIn("qkd_kvs_emb_rope_ovl", r)
        self.assertIn("qkd_kvs_emb_ctx", r)          # not named before the mark
        self.assertIn("ot_hbm_keep", r)              # lowercase prose 'superseded' is not a mark
        self.assertTrue(r["ot_hbm_keep"]["unattended"])


if __name__ == "__main__":
    unittest.main()


def test_plan_agent_maps_bottom_up_lineage():
    assert A.plan_agent("dsdv_gunit", "s81", "parent open, leaves under way") == "PLAN-S81"
    assert A.plan_agent("ot_hbm_hc_bankq0_static", "-", "cancelled only") == "PLAN-HBM"
    assert A.plan_agent("qfd_c_b16_rgx", "-", "-") == "PLAN-QC"
    assert A.plan_agent("qkd_kvs_grp_h", "qwen_kvsys", "needs redesign") == "PLAN-KV"
    assert A.plan_agent("qkd_kvs_emb", "qwen_kvsys", "needs redesign") is None   # leaf: stays with its owner
