"""HEAD-CORE-R19: lane_residual (GEOM-25 cond. 1) on the adopted M9 12.96@34.56 grid."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_mesh_r3 as H  # noqa: E402

PLAN = {"die": {"pg": {"grid": [{"layer": "M8", "width_um": 0.48, "pitch_um": 4.32, "offset_um": 2.16},
                                {"layer": "M9", "width_um": 12.96, "pitch_um": 34.56, "offset_um": 17.28}]}}}
VSS = 17.28 + 17.28          # VSS centre = offset + pitch/2


def test_band_edges_and_off_band():
    S = [("M9", VSS + 8.0, 0, 1, "c"), ("M9", VSS - 7.8, 0, 1, "c"), ("M9", VSS + 4.0, 0, 1, "c"),
         ("M9", 17.28, 0, 1, "c"), ("M8", 2.16 + 2.16 + 1.07, 0, 1, "r")]
    out, off = H.lane_residual(S, PLAN)
    assert out["M9"]["band_rel_vss_um"] == [[7.8, 8.64], [-8.64, -7.8]]
    assert out["M9"]["off_band"] == 2 and out["M8"]["off_band"] == 0
    assert {round(o["fixed_um"], 3) for o in off} == {round(VSS + 4.0, 3), 17.28}
    assert abs(out["M9"]["max_residual_um"] - 8.64) < 1e-3     # strap on the VDD centre: 8.64 to the nearest lane


if __name__ == "__main__":
    test_band_edges_and_off_band()
    print("PASS")
