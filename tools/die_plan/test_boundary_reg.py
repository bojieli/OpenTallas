"""BOUNDARY-REG-50 (COORD 19:25 FABLE-RC-KV item 3): every ft out pin gets a station within 50 um; report-only advisory
and an apply_ops planner that MOVEs the slot's last station to the out face (hop <= reach) or ADDs one."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import boundary_reg as B  # noqa: E402

W, H = 400.0, 300.0
CELL = [1.08, 0.27]


def _slot(regs, n_groups, width=4):
    bs = [[[r[0] + i * 1.08, r[1]] for i in range(width + 1)] for r in regs[len(regs) - n_groups:]]
    return dict(name="ft0", in_face="W", out_face="E", width=width, stations=len(regs), regs_um=[list(r) for r in regs],
                bit_sites_um=bs, bit_site_cell_um=CELL)


def _pins(width=4, x=W, y0=150.0):
    return {"ft0": [(b, x, y0 + b * 0.54, "E") for b in range(width + 1)]}


def _patch(monkeypatch, t, pins, regs=None):
    P = types.SimpleNamespace(types={"T": t})
    monkeypatch.setattr(B, "_plan", lambda raw, plan_path: P)
    monkeypatch.setattr(B, "out_pins", lambda P_, tn: pins)
    monkeypatch.setattr(B, "planned_regs", lambda P_, tn: regs if regs is not None else
                        [tuple(r) for s in t["ft_slots"] for r in s["regs_um"]])
    return P


def _apply(t, ops):
    for o in ops:
        parts = o["path"].split("/")
        tgt = t["ft_slots"][int(parts[4])]
        assert tgt.get(parts[5], 1 if parts[5] == "stations" else None) == o["old"]
        tgt[parts[5]] = o["value"]


def test_far_last_station_is_reported(monkeypatch):
    t = dict(outline_um=[W, H], ft_slots=[_slot([(2, 150), (100, 150), (200, 150)], 2)], hard_cores=[])
    _patch(monkeypatch, t, _pins())
    lines = B.findings({}, "p.json")
    assert any("WARN ADV-BOUNDARY-REG-50 T: 5 ft out bit(s) on 1 slot(s)" in x for x in lines)
    assert "1 type(s), 1 ft slot(s), 5 out bit(s)" in lines[-1]
    monkeypatch.setenv("OT_BREG_BLOCK", "1")
    assert any(x.startswith("FAIL ADV-BOUNDARY-REG-50 T:") for x in B.findings({}, "p.json"))


def test_move_last_station_when_hop_fits(monkeypatch):
    t = dict(outline_um=[W, H], ft_slots=[_slot([(2, 150), (100, 150), (200, 150)], 2)], hard_cores=[])
    _patch(monkeypatch, t, _pins())
    ops, rep = B.plan_ops({}, "p.json", reach=405.0)
    assert [r[2] for r in rep] == ["MOVE"]
    _apply(t, ops)
    s = t["ft_slots"][0]
    assert s["stations"] == 3 and len(s["regs_um"]) == 3 and len(s["bit_sites_um"]) == 2
    for b, x, y, _f in _pins()["ft0"]:
        cx, cy = s["bit_sites_um"][-1][b][0] + CELL[0] / 2, s["bit_sites_um"][-1][b][1] + CELL[1] / 2
        assert abs(cx - x) + abs(cy - y) <= B.RADIUS_UM
        assert s["bit_sites_um"][-1][b][0] + CELL[0] <= W
    for x, y in s["bit_sites_um"][-1]:
        assert abs(x / B.GRID_X - round(x / B.GRID_X)) < 1e-6 and abs(y / B.GRID_Y - round(y / B.GRID_Y)) < 1e-6
    assert len({tuple(q) for q in s["bit_sites_um"][-1]}) == 5
    _patch(monkeypatch, t, _pins())
    assert "0 type(s)" in B.findings({}, "p.json")[-1]


def test_add_station_when_hop_too_long(monkeypatch):
    t = dict(outline_um=[W, H], ft_slots=[_slot([(2, 150), (40, 150)], 1)], hard_cores=[])
    _patch(monkeypatch, t, _pins())
    ops, rep = B.plan_ops({}, "p.json", reach=300.0)
    assert [r[2] for r in rep] == ["ADD"]
    _apply(t, ops)
    s = t["ft_slots"][0]
    assert s["stations"] == 3 and len(s["regs_um"]) == 3 and len(s["bit_sites_um"]) == 2
    assert "(> reach: LEG405)" in rep[0][3]       # 40 -> ~398 um is over the 300 um reach: listed, not hidden


def test_sites_avoid_cores_and_other_slots(monkeypatch):
    core = dict(inst="c", origin_um=[392.0, 140.0], outline_um=[8.0, 4.0])
    t = dict(outline_um=[W, H], ft_slots=[_slot([(2, 150), (100, 150), (200, 150)], 2)], hard_cores=[core])
    _patch(monkeypatch, t, _pins())
    ops, rep = B.plan_ops({}, "p.json")
    _apply(t, ops)
    for x, y in t["ft_slots"][0]["bit_sites_um"][-1]:
        assert not (387.0 < x + CELL[0] and x < 405.0 and 135.0 < y + CELL[1] and y < 149.0)


def test_covered_by_any_planned_register_is_not_reported(monkeypatch):
    # precheck BOUNDARY-REG reading: any planned register within the radius covers the pin
    t = dict(outline_um=[W, H], ft_slots=[_slot([(2, 150), (100, 150), (200, 150)], 2)], hard_cores=[])
    _patch(monkeypatch, t, _pins(), regs=[(398.0, 151.0)])
    assert "0 type(s)" in B.findings({}, "p.json")[-1]
    assert B.plan_ops({}, "p.json") == ([], [])


def test_unseatable_slot_is_skipped_whole(monkeypatch):
    t = dict(outline_um=[W, H], ft_slots=[_slot([(2, 150), (100, 150), (200, 150)], 2)], hard_cores=[])
    _patch(monkeypatch, t, {"ft0": [(0, W, 150.0, "E"), (7, W, 151.0, "E")]})
    ops, rep = B.plan_ops({}, "p.json")
    assert ops == [] and rep[0][2] == "SKIP"
