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


if __name__ == "__main__":
    unittest.main()
