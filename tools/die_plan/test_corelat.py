"""CORELAT 10-25: declared core latencies are per corner.  A core tap's early shift is core insertion minus the die
common latency AT THAT CORNER (FF = insertion_ff_ps - clock.insertion_ff_ps; 0.81 x TT only when a value is absent),
and the die clock's STA balance keeps the contracted early shift instead of padding it away."""
import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_clock as DC  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

PAIR = HERE / "examples" / "s81_pair" / "s81_pair_plan.json"


def pair_with_core(tt=330.0, ff=260.0, die_ff=None):
    raw = json.loads(PAIR.read_text())
    ck = raw["partition_types"]["fa"]["clock"]
    tap = dict(name="u_c", kind="core", xy=[300.0, 900.0], insertion_ps=tt, insertion_tol_ps=40.0)
    if ff is not None:
        tap["insertion_ff_ps"] = ff
    ck.update(core_taps="early", taps=[tap])
    if die_ff is not None:
        raw["clock"]["insertion_ff_ps"] = die_ff
    return raw


def test_early_per_corner():
    P = S.Plan(pair_with_core(430.0, 350.0))
    tp = P.types["fa"]["clock"]["taps"][0]
    assert S.common_latency_ps(P, "TT") == 250.0 and S.common_latency_ps(P, "FF") == 202.5
    assert S.core_tap_early_ps(P, tp) == 180.0 == S.core_tap_early_ps(P, tp, "TT")
    assert S.core_tap_early_ps(P, tp, "FF") == pytest.approx(147.5)
    # FF absent on the tap -> 0.81 x TT (the flagged fallback), die FF given explicitly -> used as is
    P2 = S.Plan(pair_with_core(520.0, None, die_ff=200.0))
    tp2 = P2.types["fa"]["clock"]["taps"][0]
    assert S.core_tap_early_ps(P2, tp2, "FF") == pytest.approx(0.81 * 520.0 - 200.0)
    with pytest.raises(ValueError):
        S.core_tap_early_ps(P, tp, "SS")
    assert gen_phys.FF_TT_INSERTION_RATIO == S.FF_TT_INSERTION_RATIO == 0.81


def test_tree_taps_carry_corner_early():
    P = S.Plan(pair_with_core(430.0, 350.0))
    T, tree = DC.build(P, leaf_um=300.0, keep=[], core_early="pad", pad="level")
    core = [t for t in tree["taps"] if t["early_ps"] > 0]
    assert len(core) == 1 and core[0]["tap"] == "clk_c0"
    assert core[0]["early_corner_ps"] == {"TT": 180.0, "FF": pytest.approx(147.5)}
    assert DC.tap_early(core[0], "FF") == pytest.approx(147.5)
    assert DC.tap_early(dict(early_ps=12.0), "FF") == 12.0          # pre-CORELAT trees: TT number


@pytest.mark.skipif(not (shutil.which("sta") or Path("~/.local/opentallas-tools/bin/sta").expanduser().is_file()),
                    reason="OpenSTA not installed")
def test_sta_balance_keeps_core_early(tmp_path):
    try:
        libdir = DC.find_libdir()
    except SystemExit:
        pytest.skip("no ASAP7 libs")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(pair_with_core(330.0, 260.0)))       # early TT 80 / FF 57.5
    a = argparse.Namespace(plan=str(plan), out=str(tmp_path / "o"), leaf_um=300.0, rep_um=450.0, core_early="pad",
                           window=DC.SPLIT_WINDOW, aware_levels=DC.AWARE_LEVELS, corner=["TT", "FF"], libdir=libdir,
                           iters=10, stop_ps=2.0, pad="sta")
    assert DC.cmd_run(a) == 0
    rep = json.loads((tmp_path / "o" / "clock_report.json").read_text())
    for c, want in (("TT", 80.0), ("FF", 57.5)):
        cr = rep["corners"][c]
        got = cr["core_early_by_contract"][f"{want:g}"]
        # the STA balance must not pad the early shift away (pre-CORELAT: delivered ~0 ps early)
        assert abs(got["delivered_min_ps"] - want) <= DC.TARGET_PS and abs(got["delivered_max_ps"] - want) <= DC.TARGET_PS
        assert cr["core_early_err_max_ps"] <= DC.TARGET_PS
        assert cr["eff_tap_skew_ps"] <= DC.TARGET_PS
        assert rep["verdict"][c]["gate"] == "PASS"
