"""Re-pin a column from its class windows without changing lane identity or slot depths."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import class_window_solve as C  # noqa: E402


def test_repin_propagates_across_repeated_type():
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    types = raw["partition_types"]
    layers = ["M6", "M4"]
    original = [400, 420]
    target = [420, 440]
    C.set_type_end(types["src"], "x_o", "E", target, layers, "lsb_low")
    C.set_type_end(types["mid"], "fx_i", "W", original, layers, "lsb_low")
    C.set_type_end(types["mid"], "fx_o", "E", original, layers, "lsb_low")
    C.set_type_end(types["sink"], "x_i", "W", original, layers, "lsb_low")
    depths = [s["stations"] for s in types["mid"]["ft_slots"]]

    report = C.solve(raw, ["src"])

    assert report["mismatches_before"] == 1
    assert report["mismatches_after"] == 0
    assert report["conflicts"] == report["overlaps"] == []
    assert [(d["type"], d["bus"]) for d in report["moved"]] == [("mid", "fx_i"), ("mid", "fx_o"), ("sink", "x_i")]
    assert [p["window_um"] for p in raw["ports"] if p["id"] in {"x0", "x1", "x2"}] == [target] * 3
    assert [s["stations"] for s in types["mid"]["ft_slots"]] == depths


def test_repin_clears_stale_ft_end_override():
    slot = dict(name="ft", layers=["M6", "M4"], in_layers=["M6"], order="lsb_low", in_order="lsb_high")
    row = {"ft_slots": [slot]}

    C.set_type_end(row, "ft_i", "W", [2.0, 8.0], ["M6", "M4"], "lsb_low")

    assert "in_layers" not in slot and "in_order" not in slot
    assert slot["in_window_um"] == [2.0, 8.0]
