"""route_supply landing-ring growth: bin edges snap float error (1393.2 // 10.8 == 128.0 in binary float).

Before the fix a one-bin W/S grow step of the ring box added zero free area once its edge sat on a bin multiple reached
by subtraction, so the ring never grew W/S past the first step and ran along the outline as a thin column
(S81 col_h9_r0 xo_i0: 1104 b / 5760 flops at the E edge -> a 50 um x 900 um column, ring V M3 p99 1.82)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_supply as rs  # noqa: E402


def test_bin_edges_snap_float_error():
    b = 10.8
    assert 1393.2 // b == 128.0                      # the float trap itself (129 * 10.8 == 1393.2)
    assert rs._bin_lo(1393.2, b) == 129
    assert rs._bin_lo(1382.4, b) == 128
    assert rs._bin_lo(1404.0 - b, b) == 129
    assert rs._bin_lo(5.0, b) == 0 and rs._bin_lo(0.0, b) == 0
    assert rs._bin_hi(1425.6, b) == 132 and rs._bin_hi(1425.61, b) == 133
    assert rs._bin_hi(0.0, b) == 0


def _plan(tmp):
    (tmp / "c.lef").write_text("MACRO c\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE 40 BY 40 ;\n"
                               "  OBS\n    LAYER M1 ;\n      RECT 0 0 40 40 ;\n  END\nEND c\nEND LIBRARY\n")
    (tmp / "a.json").write_text(json.dumps({"pins": []}))
    hc = [dict(inst="u_a", module="c", origin_um=[100, 100], outline_um=[40, 40], orient="R0", lef="c.lef",
               pins_file="a.json")]
    band = {"rect_um": [1404.0, 969.636, 1425.6, 1209.6], "width": 1104, "padded_data_storage_flops": 5760}
    P = {"schema": "opentallas.die_plan.v1", "die": {"name": "tst"},
         "partition_types": {"t": {"outline_um": [1442.88, 1226.88], "hard_cores": hc,
                                   "clock": {"landing_contract": {"bands": {"xo_i0": band}}}}}}
    (tmp / "plan.json").write_text(json.dumps(P))
    (tmp / "core_conns.json").write_text(json.dumps({"t": {"u_a": {}}}))


def test_landing_ring_grows_compact_not_a_column(tmp_path, monkeypatch):
    _plan(tmp_path)
    rings = []
    orig = rs.Grid.area_density

    def rec(self, rect, dh, dv):
        if self.cur == "ring":
            rings.append(tuple(rect))
        return orig(self, rect, dh, dv)

    monkeypatch.setattr(rs.Grid, "area_density", rec)
    rs.main([str(tmp_path / "plan.json"), "--die", "tst", "--repo", str(tmp_path), "--out", str(tmp_path / "o")])
    assert len(rings) == 1
    x0, y0, x1, y1 = rings[0]
    w, h = x1 - x0, y1 - y0
    assert w * h >= 0.95 * 57600                     # 5760 flops x 10 um2 (growth stops on whole-bin free area)
    assert w > 150, (w, h)                           # grew W (the bug stopped at 1393.2: w = 49.7)
    assert max(w, h) / min(w, h) < 2.0               # compact, not a column along the outline
