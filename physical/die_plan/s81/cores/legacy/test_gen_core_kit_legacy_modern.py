"""KITS-SPARE/S81C 10-25: gen_core_kit_legacy.py modern flow (default) vs --legacy-flow (opt-out, old kit).
    python3 -m pytest -q physical/die_plan/s81/cores/legacy/test_gen_core_kit_legacy_modern.py"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_core_kit_legacy.py"
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402

MOD = "dsdv_bksel_c"   # no macros, no hard children, plan pins from the S81 plan


def _gen(out, *extra):
    r = subprocess.run([sys.executable, str(GEN), "--module", MOD, "--out", str(out), *extra],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"])


def test_run_kit_templates():
    leg, mod = G.run_kit(False), G.run_kit(True)
    assert "@" not in leg.split("bash -lc", 1)[1].split('> "$K/run_$GOAL.log"', 1)[0]
    assert "rtl_lint" not in leg and "reg_fanout" not in leg and "OT_VCLK_CORNER" not in leg
    assert "  python3 -I /work/sdc_lint.py" in leg          # old unguarded first step, old indentation
    i_lint, i_sdc = mod.index("rtl_lint.py"), mod.index("sdc_lint.py /work")
    i_fg, i_rf, i_ff, i_goal = (mod.index("face_guard_core.py \\$N"), mod.index("reg_fanout_gate.py"),
                                mod.index("OT_VCLK_CORNER=ff"), mod.index("\\$M $GOAL"))
    assert i_lint < i_sdc < i_fg < i_rf < i_ff < i_goal


@pytest.mark.skipif(not (G.S81 / "die_plan.json").is_file(), reason="sparse checkout without the S81 plan")
def test_modern_vs_legacy_kit(tmp_path):
    leg = _gen(tmp_path / "leg", "--legacy-flow")
    mod = _gen(tmp_path / "mod", "--regional-taps", "4x2")
    lc, mc = (leg / "config.mk").read_text(), (mod / "config.mk").read_text()
    # legacy: fixed plan vclk, stock RC, tap balance + MCMM CTS repair, no new gates
    assert "LAYER_PARASITICS_FILE" not in lc and "OT_VCLK_FF" not in lc and "regional_taps" not in lc
    assert "insertion_ff_ps" not in json.loads((leg / "sdc_lint.json").read_text())
    assert not (leg / "reg_fanout_gate.py").exists() and (leg / "tap_balance.tcl").exists()
    # modern: RCX RC, per-corner binding, FF-only GRT hold, lint + reg_fanout, regional taps replace tap_balance
    for k in ("export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl", "export OT_VCLK_TT = 250.0000",
              "export OT_VCLK_FF = 202.5000", "override export POST_GLOBAL_ROUTE_TCL = /work/grt_post_core.tcl",
              "export PRE_CTS_TCL = /work/regional_taps.tcl", "export OT_RT_PROTECT_SPINE = 1", "export OT_RT_SETUP_ONLY = 1"):
        assert k in mc, k
    assert mc.rindex("export CTS_ARGS = -sink_clustering_enable -obstruction_aware") > mc.index("export CTS_ARGS")
    assert json.loads((mod / "sdc_lint.json").read_text())["insertion_ff_ps"] == 202.5
    assert json.loads((mod / "clock_binding.json").read_text())["insertion_ps"] == {"tt": 250.0, "ff": 202.5}
    for f in ("rtl_lint.py", "reg_fanout_gate.py", "setRC_rcx.tcl", "vclk_corner.tcl", "regional_taps.tcl",
              "regional_taps_balance.tcl", "clock_spine_guard.tcl"):
        assert (mod / f).is_file(), f
    assert not (mod / "tap_balance.tcl").exists() and not (mod / "hold_budget.tcl").exists()
    assert "post_grt_drv.tcl" in (mod / "grt_post_core.tcl").read_text()
    subprocess.run(["bash", "-n", str(mod / "run_kit.sh")], check=True)
    # modern without regional taps: tap balance stays, CTS repair is setup-only (hold only in the FF frame)
    m2 = _gen(tmp_path / "m2")
    assert "repair_timing_helper -setup" in (m2 / "cts_post.tcl").read_text()
    assert "repair_timing_helper -setup" not in (leg / "cts_post.tcl").read_text()
