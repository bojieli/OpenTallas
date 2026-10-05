import ast
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w19_rank_dispatch as D

QUADS = json.loads((ROOT / "results/floorplan/hbm_gpu/v41_hbm_die.json").read_text())["quadrants"]
IDS = [61, 69, 112, 170, 299, 357]


def test_all_rank_rows_and_physical_expert_address_nonoverlap():
    # Execute the actual pinned ISA partition helper without importing golden.
    tree = ast.parse((ROOT / "tools/w19_hbm_tp96_isa.py").read_text())
    fn = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "even")
    namespace = {"TP": 96}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "pinned ISA even", "exec"), namespace)
    coverage = {op: [] for op in D.OPS}
    for rank in range(96):
        layout = D.rank_layout(rank, QUADS)
        for stack, segments in layout.items():
            assert segments
            stride = segments[0]["cfg_exp_lines"]
            for expert in (0, 383):
                previous = (17 + expert * stride) * 4
                for segment in segments:
                    start = (17 + expert * stride + segment["cfg_off"]) * 4
                    assert start == previous
                    previous = start + segment["cfg_lines"] * 4
                assert previous == (17 + (expert + 1) * stride) * 4
            for segment in segments:
                op, (lo, hi) = segment["operation"], segment["rows"]
                owner = namespace["even"](D.OPS[op][0])[rank]
                assert owner[0] <= lo < hi <= owner[1]
                assert segment["sm"] in QUADS[str(stack)]
                coverage[op].extend(range(lo, hi))
    for op, (rows, _) in D.OPS.items():
        assert sorted(coverage[op]) == list(range(rows))


@pytest.mark.parametrize("ids", [IDS[::-1], [61]*6, IDS[:5], IDS[:-1]+[384]])
def test_invalid_route_selection(ids):
    with pytest.raises(ValueError):
        D.dispatch(D.rank_layout(0, QUADS), ids, stage="input", enable=True)


def test_default_off_and_producer_boundary():
    layout = D.rank_layout(0, QUADS)
    with pytest.raises(ValueError, match="off"):
        D.dispatch(layout, IDS, stage="input")
    with pytest.raises(ValueError, match="completion"):
        D.dispatch(layout, IDS, stage="output", enable=True)
    descriptors = D.dispatch(layout, IDS, stage="input", enable=True)
    descriptors += D.dispatch(layout, IDS, stage="output", producer_ready=True, enable=True)
    one = [x for x in descriptors if x["sm"] == 0]
    assert len(one) == 18
    assert [(x["expert_id"], x["operation"]) for x in one[:12]] == [(e, op) for e in IDS for op in ("w1", "w3")]
    assert all(x["operation"] == "w2" for x in one[12:])
    assert one[0]["payloads"] == 24 and one[-1]["payloads"] == 32


def test_stack_ownership_and_port_bounds():
    with pytest.raises(ValueError):
        D.rank_layout(96, QUADS)
    with pytest.raises(ValueError):
        D.rank_layout(0, QUADS, base_line=1 << 22)
    bad = dict(QUADS, **{"1": QUADS["0"]})
    with pytest.raises(ValueError):
        D.rank_layout(0, bad)
