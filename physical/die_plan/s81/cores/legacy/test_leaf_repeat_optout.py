"""KW-FIX-24/LEAFOPT 11-06 (COORD 21:0x (1)): an S81 regional-tap kit (recipe regional_taps / --regional-taps: the
planned trunk + H-tree + regional taps own the clock tree) opts out of the default-on clk_leaf_repeat in config.mk;
a normal type kit of the same generator keeps the default (no OT_CLK_LEAF_REPEAT line).
    python3 -m pytest -q physical/die_plan/s81/cores/legacy/test_leaf_repeat_optout.py"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_core_kit_legacy.py"
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402
import core_flow  # noqa: E402  (tools/die_plan, put on sys.path by the generator)

MOD = "dsdv_bksel_c"   # no macros, no hard children, plan pins from the S81 plan (as test_gen_core_kit_legacy_modern)


def _gen(out, *extra):
    r = subprocess.run([sys.executable, str(GEN), "--module", MOD, "--out", str(out), *extra],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return (Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"]) / "config.mk").read_text().splitlines()


@pytest.mark.skipif(not (G.S81 / "die_plan.json").is_file(), reason="sparse checkout without the S81 plan")
def test_regional_tap_kit_opts_out_normal_kit_default(tmp_path):
    rt = _gen(tmp_path / "rt", "--regional-taps", "4x2")
    assert "export PRE_CTS_TCL = /work/regional_pre_cts.tcl" in rt
    assert rt.count(core_flow.LEAF_REPEAT_OPTOUT) == 1
    i = rt.index(core_flow.LEAF_REPEAT_OPTOUT)
    assert "KW-FIX-24/LEAFOPT (COORD 21:0x): S81 regional-tap kit" in rt[i - 1]
    plain = _gen(tmp_path / "plain")
    assert not any("regional_taps" in ln for ln in plain)
    assert not any("OT_CLK_LEAF_REPEAT" in ln for ln in plain)


def test_optout_helper_respects_existing_value():
    c = ["export OT_CLK_LEAF_REPEAT = 1"]
    assert core_flow.leaf_repeat_plan_optout(c, "x") is False and c == ["export OT_CLK_LEAF_REPEAT = 1"]
    c = ["override export OT_CLK_LEAF_REPEAT := 1"]
    assert core_flow.leaf_repeat_plan_optout(c, "x") is False and len(c) == 1
    c = ["export OT_CLK_LEAF_GRT = 0"]
    assert core_flow.leaf_repeat_plan_optout(c, "x") is True and c[-1] == "export OT_CLK_LEAF_REPEAT = 0"
