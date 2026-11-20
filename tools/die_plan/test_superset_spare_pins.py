"""SUPERSET-1 (FABLE-SUPERSET-0415): a superset type gets pins for the declared bus / ft-slot ends no die port binds."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as GP  # noqa: E402
import schema as S  # noqa: E402


def plan(superset):
    t = dict(module="m", outline_um=[172.8, 86.4],
             buses=[dict(name="a", dir="in", width=4, kind="data", face="N", window_um=[17.28, 34.56], layers=["M7", "M5"])],
             ft_slots=[dict(name="ft0", width=3, stations=2, in_face="S", out_face="N", in_window_um=[69.12, 86.4],
                            out_window_um=[103.68, 120.96], layers=["M7", "M5"])])
    if superset:
        t["superset"] = {"class": "test"}
    return SimpleNamespace(types={"t": t}, parts={"p0": dict(name="p0", type="t", origin_um=[0.0, 0.0], orient="R0")}, ports={},
                           layers={L["name"]: L for L in S.ASAP7_LAYERS}, ptype=lambda inst: t, rect=None)


def test_type_without_the_key_is_unchanged():
    assert GP.type_pins(plan(False), "t") == []


def test_spare_ends_get_window_pins_on_their_own_faces():
    pins = GP.type_pins(plan(True), "t")
    by = {}
    for bus, bit, ln, x, y, f in pins:
        by.setdefault(bus, []).append((bit, ln, x, y, f))
    assert sorted(by) == ["a", "ft0_i", "ft0_o"]
    assert len(by["a"]) == 5 and len(by["ft0_i"]) == 4 and len(by["ft0_o"]) == 4      # data + the epoch pin
    assert all(f == "N" and y == 86.4 and 17.28 <= x <= 34.56 for _b, _l, x, y, f in by["a"])
    assert all(f == "S" and y == 0.0 and 69.12 <= x <= 86.4 for _b, _l, x, y, f in by["ft0_i"])
    assert all(f == "N" and y == 86.4 and 103.68 <= x <= 120.96 for _b, _l, x, y, f in by["ft0_o"])
    assert {ln for _b, ln, *_ in by["ft0_i"]} == {"M7", "M5"}
    assert len({(ln, x) for _b, ln, x, _y, _f in by["a"]}) == 5                      # one track per pin


def test_a_bound_end_keeps_its_port_pins():
    spare = GP.superset_spare_pins(plan(True), "t", {"a", "ft0_i"})
    assert {b for b, *_ in spare} == {"ft0_o"}


def test_spare_end_without_geometry_is_named():
    p = plan(True)
    del p.types["t"]["ft_slots"][0]["out_window_um"]
    try:
        GP.type_pins(p, "t")
    except ValueError as e:
        assert "ft0_o" in str(e)
    else:
        raise AssertionError("no error")
