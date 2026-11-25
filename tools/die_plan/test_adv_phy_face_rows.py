"""ADV-PHY-FACE-ROWS (FP-CONVERGE-QC 11-25): phy_serdes shape fires, a band on the port face passes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_phy_face_rows as P  # noqa: E402
import plan_advisory as PA  # noqa: E402


def plan(origin_y, h=2320.056, outline_h=2324.16, face="N"):
    bus = [dict(name="tx_flit", width=597, face=face, window_um=[909.0, 1034.0]), dict(name="rx_flit", width=597, face=face, window_um=[782.0, 907.0])]
    t = dict(outline_um=[1563.84, outline_h], buses=bus,
             contents=[dict(inst="u_io", module="phy", lef="x.lef", origin_um=[0.0, origin_y], outline_um=[1563.57, h])])
    return {"partition_types": {"phy_serdes": t}}


def test_pass_band_on_port_face():          # phy_serdes_b: macro at y 0, 4.1 um free on the N face
    assert P.findings(plan(0.0), "p.json") == []


def test_far_side_mutant_fires():          # phy_serdes: macro flush with N, rows only in the 4.1 um S strip
    out = P.findings(plan(4.104), "p.json")
    assert out[0].startswith("WARN ADV-PHY-FACE-ROWS FACE-STARVED FAR-SIDE phy_serdes: face N strip 0.00 um") and "opposite face S strip 4.10" in out[0]
    assert out[-1].startswith("LIST ADV-PHY-FACE-ROWS 1 ")


def test_both_faces_blocked_not_far_side():
    out = P.findings(plan(0.0, h=2324.16), "p.json")
    assert out[0].startswith("WARN ADV-PHY-FACE-ROWS FACE-STARVED phy_serdes") and "FAR-SIDE" not in out[0]


def test_soft_types_ignored():
    raw = {"partition_types": {"t": {"outline_um": [100.0, 100.0], "contents": [{"module": "m", "origin_um": [0, 0], "outline_um": [100.0, 100.0]}],
                                     "buses": [dict(name="b", width=5000, face="N", window_um=[0.0, 50.0])]}}}
    assert P.findings(raw, "p.json") == []


def test_registered_in_plan_advisory():
    assert ("PHY-FACE-ROWS", "adv_phy_face_rows") in PA.CHECKS
