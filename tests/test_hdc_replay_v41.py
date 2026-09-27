"""tools/hdc_replay_v41.py: the shape-generic V4.1 program equals the real builder at the reduced shape, and
the shipped-shape replay responds to the design options in the right direction."""
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hdc_replay_v41 as R  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402


@pytest.fixture(scope="module")
def layout():
    import hdc_golden_v41 as V
    if not V.CHECKPOINT.exists():
        pytest.skip("reduced V4.1 checkpoint not built")
    import hdc_program_v41 as P
    return P.Layout(V.Model())


@pytest.mark.parametrize("lanes", [4, 8, 16])
def test_reduced_program_equivalence(layout, lanes):
    for pos in (7, 101):
        v = R.validate(pos=pos, lanes=lanes, layout=layout)
        assert v["field_mismatches"] == 0, v["first_mismatches"]
        assert v["hdc_timing_v41"] == v["this_simulate_real_program"] == v["this_simulate_emitted_program"]


def _cycles(cfg, pos=199999, layers=(0, 20), eng=True):
    prog = R.build(R.SHIPPED, cfg.su_lanes, eng, layers=list(layers), embed=False, head=False)
    return R.simulate(prog, pos, R.SHIPPED, cfg)


def test_shipped_monotonic_in_widths():
    C = R.Cfg()
    base = _cycles(C)
    for opt in (dict(su_lanes=64), dict(mac_rate=4096.0), dict(kv_rate=4096.0), dict(sel_lanes=64)):
        assert _cycles(replace(C, **opt)) <= base, opt
    assert _cycles(replace(C, su_lanes=64)) >= _cycles(replace(C, su_lanes=512))
    B = R.Cfg(su_lanes=512, mac_rate=276000.0, kv_rate=276000.0, sel_lanes=64)
    assert _cycles(B, eng=False) < base
    assert _cycles(replace(B, red_parallel=True), eng=False) <= _cycles(B, eng=False)


def test_context_grows_indexer_work():
    C = R.Cfg()
    assert _cycles(C, pos=8191) < _cycles(C, pos=199999) < _cycles(C, pos=1048575)


def test_dyn_values_shipped():
    d = R.dyn_values(R.SHIPPED, 199999)
    assert d["WIN"] == 128 and d["NS2"] == 512 and d["T2"] == 640
    assert d["SC2"] == 25000 and d["SCR"] == 4096
    assert I.W_LANES == 16
