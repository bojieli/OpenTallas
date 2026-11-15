"""KV-RAWFIX 11-15: kv_start_corridor_event.py raw_type three-part rule (synthetic type, no bind needed).
1. a raw relay without a "depth N @ (x, y)" comment takes depth/site from its driver;
2. an origin target inside a keepout falls back to the cland_tstart_in pin;
3. a consumer target inside a keepout or outside the core area moves to the nearest free point inside the core area."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "die_plan"))
import kv_start_corridor_event as K  # noqa: E402

W, H, M = 800.0, 800.0, 4.32
BOX = (300.0, 0.0, 500.0, 200.0)     # a macro on the S edge (closed to the edge by corridor_obstacles)


def _inside_grown(q, obs):
    c = K.CLEAR_UM
    return any(a - c < q[0] < cc + c and b - c < q[1] < d + c for a, b, cc, d in obs)


def test_free_point_untouched_when_free():
    assert K._core_free_point((100.0, 100.0), [list(BOX)], W, H, M) == (100.0, 100.0)


@pytest.mark.parametrize("p", [(400.0, 2.656), (400.0, 100.0), (305.0, 150.0), (-5.0, 400.0), (400.0, 900.0)])
def test_free_point_inside_core_outside_keepout(p):
    obs = [list(BOX)]
    q = K._core_free_point(p, obs, W, H, M)
    assert q is not None
    assert M <= q[0] <= W - M and M <= q[1] <= H - M
    assert not _inside_grown(q, obs)
    assert abs(q[0] - p[0]) + abs(q[1] - p[1]) < 150     # nearest, not a far jump


def _type(monkeypatch):
    monkeypatch.setattr(K, "macro_boxes", lambda t: {"m0": BOX})
    return {"outline_um": [W, H], "clock": {"landing_contract": {
        "pins": [{"name": "cland_tstart_in", "xy_um": [400.0, 300.0]},
                 {"name": "cland_fstart_out_s0", "xy_um": [400.0, 2.656]},
                 {"name": "cland_fstart_out_s1", "xy_um": [700.0, 500.0]}],
        "bands": {}}}}


RTL = """assign cland_start_raw = cland_reset_ft0_i;
ot_dp_rrelay a0 (.clk(clk), .d(rst_in), .q(r1)); // reset depth 1 @ (790.0, 400.0)
ot_dp_rrelay a1 (.clk(clk), .d(r1), .q(r2)); // reset depth 2 @ (790.0, 400.0)
ot_dp_rrelay u_cland_rst_ft0 (.clk(clk), .d(r2), .q(cland_reset_ft0_i));
"""


def test_raw_rule(tmp_path, monkeypatch):
    t = _type(monkeypatch)
    (tmp_path / "ty_part.sv").write_text(RTL)
    rep = K.raw_type({}, "ty", t, tmp_path, M, 10.8)
    assert rep["raw"] == "cland_reset_ft0_i" and rep["chain_depth"] == 3      # part 1: r1, r2, comment-less raw relay
    br = {b["name"]: b for b in t["clock"]["landing_raw_branches"]}
    assert set(br) == {"o", "fs_s0", "fs_s1"}
    c = rep["consumers"]
    # part 2: (400, EDGE_Y) is under the macro closed to the S edge -> origin target is the pin itself (free there)
    assert "target_um" not in c["origin"]
    # part 3: fstart s0 pin (400, 2.656) is inside the keepout and the core margin -> moved, inside the core area
    tx, ty = c["fstart:s0"]["target_um"]
    assert c["fstart:s0"]["pin_offset_um"] > 0 and ty >= M
    assert not _inside_grown((tx, ty), K.corridor_obstacles(t, M, 10.8))
    assert "target_um" not in c["fstart:s1"]
    assert all(v["max_hop_um"] <= K.MAX_HOP_UM for v in c.values())


def test_raw_rule_part1_needs_driver(tmp_path, monkeypatch):
    t = _type(monkeypatch)
    (tmp_path / "ty_part.sv").write_text(RTL.replace(".d(r2)", ".d(zz)"))
    with pytest.raises(SystemExit):
        K.raw_type({}, "ty", t, tmp_path, M, 10.8)
