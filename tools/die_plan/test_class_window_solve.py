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


def _column(target, original):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    types = raw["partition_types"]
    layers = ["M6", "M4"]
    C.set_type_end(types["src"], "x_o", "E", target, layers, "lsb_low")
    C.set_type_end(types["mid"], "fx_i", "W", original, layers, "lsb_low")
    C.set_type_end(types["mid"], "fx_o", "E", original, layers, "lsb_low")
    C.set_type_end(types["sink"], "x_i", "W", original, layers, "lsb_low")
    return raw


def test_two_anchors_conflict_without_column_mode():
    raw = _column([420, 440], [400, 420])
    report = C.solve(raw, ["src", "mid"])
    assert report["conflicts"] and all(m["type"] != "mid" for m in report["moved"])


def test_column_mode_weaker_anchor_takes_stronger_window_and_propagates():
    """UNIFY-TOOLS whole column: src and mid are both class rows; src is stronger, so mid's ends move to src's window
    and the move propagates on to sink in the same pass; no conflict."""
    target = [420, 440]
    raw = _column(target, [400, 420])
    report = C.solve(raw, ["src", "mid"], column=True)
    assert report["conflicts"] == [] and report["overlaps"] == []
    assert [(d["type"], d["bus"]) for d in report["moved"]] == [("mid", "fx_i"), ("mid", "fx_o"), ("sink", "x_i")]
    assert report["mismatches_after"] == 0
    assert [p["window_um"] for p in raw["ports"] if p["id"] in {"x0", "x1", "x2"}] == [target] * 3


def test_column_mode_order_decides_the_winner():
    raw = _column([420, 440], [400, 420])
    report = C.solve(raw, ["mid", "src"], column=True)
    assert ("src", "x_o") in [(d["type"], d["bus"]) for d in report["moved"]]
    assert report["conflicts"] == [] and report["mismatches_after"] == 0
