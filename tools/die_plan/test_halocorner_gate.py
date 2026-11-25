"""HALOCORNER-1125 (COORD, QC-ALLFIX; FLOW-OPS-R3 DIEPLAN-GREEN 11-24 23:33): PRE reports (WARN, report-only) every planned relay
site / reset-tree node on a shared corner of 2+ grown halos, the points reset_tree._free calls legal although they hold no
row-high / cell-wide run.  _free itself is unchanged here."""
import json
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402

CX, CY = 825.12, 816.48                                   # q_su31: four halo boxes meet here
FOUR = [(700.0, 700.0, CX, CY), (CX, 700.0, 950.0, CY), (700.0, CY, CX, 950.0), (CX, CY, 950.0, 950.0)]


def test_four_halo_corner_is_flagged():
    assert G.halo_corner_hit((CX, CY), FOUR) == 4
    assert G.halo_corner_hit((CX, 816.4799999999999), FOUR) == 4          # decimal roundoff of abutting faces


def test_clean_points_not_flagged():
    assert G.halo_corner_hit((CX, CY), FOUR[:1]) == 0                      # corner of ONE halo: a legal face site
    assert G.halo_corner_hit((CX + 5.0, CY + 5.0), FOUR) == 0              # interior: another class, not this one
    assert G.halo_corner_hit((600.0, 600.0), FOUR) == 0                    # open area
    assert G.halo_corner_hit((CX, 690.0), FOUR) == 0                       # below the corners, touching nothing
    two_apart = [(0.0, 0.0, 100.0, 100.0), (110.0, 0.0, 200.0, 100.0)]    # 10 um channel: corner of each, touches one
    assert G.halo_corner_hit((100.0, 100.0), two_apart) == 0


def test_two_halo_cases_per_the_real_rule():
    diag = [(0.0, 0.0, 100.0, 100.0), (100.0, 100.0, 200.0, 200.0)]       # corners meet: zero-height and zero-width run
    assert G.halo_corner_hit((100.0, 100.0), diag) == 2
    seam = [(0.0, 0.0, 100.0, 100.0), (60.0, 100.0, 200.0, 200.0)]        # C1n sle_st_a: halos stacked on one seam, offset in x
    assert G.halo_corner_hit((60.0, 100.0), seam) == 2                     # seam ends: a corner of one halo, zero-height run
    assert G.halo_corner_hit((100.0, 100.0), seam) == 2
    assert G.halo_corner_hit((80.0, 100.0), seam) == 0                     # mid-seam: no corner; reset_tree._free already rejects it
    assert G.halo_corner_hit((100.0, 50.0), [(0.0, 0.0, 100.0, 100.0)]) == 0      # one halo face: legal (CLEAR_UM is inside)


def _plan(root, pts_tree, relay_sites, in_site=None):
    """one type with four clock keepouts whose grown halos (8.64) meet at (108.64, 108.64)"""
    k = [[0.0, 0.0, 100.0, 100.0], [117.28, 0.0, 217.28, 100.0], [0.0, 117.28, 100.0, 217.28], [117.28, 117.28, 217.28, 217.28]]
    ty = {"module": "m", "outline_um": [300.0, 300.0], "contents": [], "hard_cores": [], "relay_sites": relay_sites,
          "clock": {"keepouts_um": k, "landing_contract": {"collector_tree": {
              "root": [8.16, 8.608], "relays": [{"name": f"u_rrl_{i}", "xy": xy} for i, xy in enumerate(pts_tree)], "outs": []}}}}
    raw = {"die": {"name": "qwen_compute"}, "reset": {"in_sites": {"t": in_site} if in_site else {}}, "partition_types": {"t": ty}}
    p = Path(root) / "plan.json"
    p.write_text(json.dumps(raw))
    return str(p)


def test_plan_lists_offenders_report_only(tmp_path):
    p = _plan(tmp_path, [[108.64, 108.64], [250.0, 250.0]], {"u_a/q": [108.64, 108.64], "u_b/q": [250.0, 20.0]}, in_site=[108.64, 108.64])
    f = G.check_halocorner(p)
    warn = [x for x in f if x.startswith("WARN HALOCORNER")]
    assert len(warn) == 1 and "qwen_compute/t: 3 relay site(s)" in warn[0] and "at 1 shared halo corner(s)" in warn[0]
    assert "reset_tree:u_rrl_0 (108.64, 108.64) x4" in warn[0] and "relay_sites:u_a/q" in warn[0] and "reset_in_site" in warn[0]
    assert "u_rrl_1" not in warn[0] and "u_b/q" not in warn[0]
    assert f[-1] == "LIST HALOCORNER die qwen_compute types 1 points 6 flagged 3 at 1 corner(s) in 1 type(s)"
    assert not any(x.startswith("FAIL") for x in f)                         # report-only


def test_clean_plan_silent_and_skippable(tmp_path):
    p = _plan(tmp_path, [[250.0, 250.0]], {"u_b/q": [250.0, 20.0]})
    f = G.check_halocorner(p)
    assert not any(x.startswith("WARN") for x in f) and "flagged 0" in f[-1]
    assert "HALOCORNER" in G.CLASSES                                         # --skip HALOCORNER
