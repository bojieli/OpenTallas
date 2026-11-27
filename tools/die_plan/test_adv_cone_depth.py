"""C-CONE-DEPTH (QC-INT-R2-TOOLS 11-26): word-level cone depth lint on a yosys-json fixture."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_cone_depth as CD  # noqa: E402


def cell(t, a, b, y, aw=32, bw=32):
    return {"type": t, "parameters": {"A_WIDTH": format(aw, "032b"), "B_WIDTH": format(bw, "032b")},
            "port_directions": {"A": "input", "B": "input", "Y": "output"}, "connections": {"A": a, "B": b, "Y": y}}


def dff(d, q):
    return {"type": "$dff", "parameters": {}, "port_directions": {"CLK": "input", "D": "input", "Q": "output"}, "connections": {"CLK": [2], "D": d, "Q": q}}


def chain(n, t="$add"):
    """reg q0 -> n chained cells -> reg"""
    cells = {"r0": dff([100], [101])}
    prev = [101]
    for i in range(n):
        out = [200 + i]
        cells[f"c{i}"] = cell(t, prev, [101], out)
        prev = out
    cells["r1"] = dff(prev, [999])
    return {"cells": cells, "netnames": {"deep_q": {"bits": [200 + n - 1]}}}


def test_levels_by_type():
    assert CD.cell_levels(cell("$and", [1], [2], [3])) == 1
    assert CD.cell_levels(cell("$add", [1], [2], [3])) == 2 * 5 + 2
    assert CD.cell_levels(cell("$eq", [1], [2], [3])) == 6
    assert CD.cell_levels(cell("$mul", [1], [2], [3])) == 22


def test_chain_depth_and_endpoint():
    lv, where, n = CD.module_depth(chain(3))
    assert lv == 36 and where == "deep_q" and n == 3
    assert CD.module_depth({"cells": {"r": dff([1], [2])}}) == (0.0, "", 0)


def test_sequential_cells_break_paths():
    m = chain(2)
    m["cells"]["r_mid"] = dff([200], [201])         # a register in the middle: second cell starts from a fresh path? (c1 reads c0 out directly)
    lv, _, _ = CD.module_depth(m)
    assert lv == 24


def test_comb_loop_does_not_hang():
    a, b = cell("$and", [5], [1], [6]), cell("$and", [6], [1], [5])
    lv, _, _ = CD.module_depth({"cells": {"a": a, "b": b}})
    assert lv >= 1


def test_judge_flags_over_budget_with_plan_types(tmp_path):
    raw = {"die": {"period_ps": 833}, "partition_types": {"sle_x": {"module": "deepmod"}, "sle_y": {"module": "okmod"}}}
    yj = {"modules": {"$paramod$ab\\deepmod": dict(chain(40), attributes={"hdlname": "deepmod"}), "okmod": chain(1)}}
    rows, budget, ps, n = CD.judge(raw, yj)
    assert budget == 703.0 and n == 2 and [r[0] for r in rows] == ["deepmod"] and rows[0][5] == ["sle_x"]
    p = tmp_path / "asbuilt.json"
    p.write_text(json.dumps(yj))
    lines = CD.findings(raw, "plan.json", yosys_json=str(p))
    assert lines[0].startswith("WARN ADV-CONE-DEPTH deepmod:") and "plan types sle_x" in lines[0]
    assert lines[-1].startswith("LIST CONE-DEPTH deepest 480 levels (deepmod); modules judged 2 flagged 1") and "plan types with elab RTL 2 of 2" in lines[-1]


def test_no_elab_json_is_silent_and_stage_env(monkeypatch):
    assert CD.findings({"partition_types": {}}, "p.json") == []
    monkeypatch.setenv("OT_CONE_STAGE_PS", "40")
    assert CD.stage_ps() == 40.0
