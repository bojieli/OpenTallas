"""R20: solver-set mc_includes_stub drives the pair_u guard; r11 HB4 count floor fix + per-endpoint sizing."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import qc_clk_mesh3 as M


def test_mc_stub_flag_from_solve_docs():
    assert M._set_mc_stub_flag([{"mc_includes_stub": False}, {"mc_includes_stub": False}]) is False
    assert M._set_mc_stub_flag([{"mc_includes_stub": True}]) is True
    M._set_mc_stub_flag([{}])
    assert M.pair_u.mc_includes_stub is False


def _hb(tmp_path):
    p = Path(__file__).resolve().parents[2] / "results/qc_clk_mesh3/r17/scripts/r11_hb_count.py"
    s = importlib.util.spec_from_file_location("r11hb", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_hb4_zero_residual_bus_gets_no_cells(tmp_path):
    H = _hb(tmp_path)
    T = dict(outline_um=[100, 100], hard_cores=[], note="fill 0.5 at util")
    plan = dict(die=dict(outline_um=[1000, 1000]), partition_types=dict(A=T, B=T),
                partitions=[dict(name="a", type="A"), dict(name="b", type="B"), dict(name="c", type="B")],
                ports=[dict(id=1, src=dict(part="a"), dst=dict(part="b", bus="x"), width=10),
                       dict(id=2, src=dict(part="a"), dst=dict(part="c", bus="x"), width=10)])
    # pair a|b needs a 30 ps pad, a|c none (demand - lib hold <= 0): type-port pads both b and c, per endpoint only b
    frag = dict(clock=dict(hold_demand=dict(pairs={"a|b": 30.0 - H.LIB_HOLD, "a|c": -H.LIB_HOLD}, default_ps=-H.LIB_HOLD)))
    (tmp_path / "p.json").write_text(json.dumps(plan))
    (tmp_path / "f.json").write_text(json.dumps(frag))
    H.main(str(tmp_path / "p.json"), str(tmp_path / "f.json"), str(tmp_path / "o.json"))
    assert json.loads((tmp_path / "o.json").read_text())["hb4_cells"] == 20
    H.main(str(tmp_path / "p.json"), str(tmp_path / "f.json"), str(tmp_path / "e.json"), per_endpoint=True)
    e = json.loads((tmp_path / "e.json").read_text())
    assert e["hb4_cells"] == 10 and e["bits_needing_fix"] == 10
    assert H.ncell(0.0, 44.0) == 0 and H.ncell(-5.0, 44.0) == 0 and H.ncell(44.6, 44.555) == 2
