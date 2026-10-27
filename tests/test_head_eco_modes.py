"""HEAD-CORE-R17: per-mode FF/TT binding of the s81_head post-route ECO (tools/s81_head/head_eco_modes.py) fails closed."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
import head_eco_modes as M  # noqa: E402

CFG_SINGLE = """export CORNER = TC
export CORNERS = tc bc
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) /work/macros/rom_tt.lib
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) /work/macros/rom_ff.lib
export OT_VCLK_TT = 250
export OT_VCLK_FF = 202.5
override export PRE_GLOBAL_ROUTE_TCL = /work/bind_ff_actual.tcl
"""
CFG_MM = CFG_SINGLE + """override export PRE_GLOBAL_ROUTE_TCL = /work/bind_ff_r14.tcl
override export CORNERS = tc BC
export OT_HOLD_MM = 1
export OT_MM_SETUP_CORNER = tc
override export OT_MM_FF_SDC = /work/vclk_ff.sdc
"""
HOOK = """set_clock_latency -source 202.5 [get_clocks vclk]
source /work/hold_pad_hb4.tcl
puts "ACTUAL_FF_BOUND 202.5; qualified HB4-only hold wrapper active"
source /work/drv.tcl
source /work/r10_hold_pass2_hook.tcl
"""
HOOK_R14 = """source /work/hold_pad_hb4.tcl
puts "R16_FF_BOUND per mode: ff from vclk_ff.sdc, ss keeps the TT contract"
source /work/drv.tcl
source /work/r10_hold_pass2_hook.tcl
source /work/head_grt_drv_unscaled.tcl
"""
SDC = """create_clock -name clk -period 833 [get_ports ft_mstrap_i]
create_clock -name vclk -period 833
set_clock_latency -source 250.0000 [get_clocks vclk]
set_input_delay -min -40 -clock vclk [all_inputs]
"""


def kit(tmp, cfg=CFG_SINGLE, hook=HOOK, lint=None, sdc=SDC, vff=None):
    k = tmp / "eco"
    k.mkdir()
    (k / "config.mk").write_text(cfg)
    (k / "bind_ff_actual.tcl").write_text(hook)
    (k / "bind_ff_r14.tcl").write_text(HOOK_R14)
    (k / "constraint.sdc").write_text(sdc)
    (k / "sdc_lint.json").write_text(json.dumps(lint or {"insertion_ps": 250.0, "insertion_ff_ps": 202.5}))
    if vff is not None:
        (k / "vclk_ff.sdc").write_text(f"set_clock_latency -source {vff} [get_clocks vclk]\n")
    return k


def written(k):
    return sorted(p.name for p in k.iterdir())


def test_single_mode_kit_converted(tmp_path):
    k = kit(tmp_path)
    assert M.main([str(k), "--ff-bound-ps", "202.5"]) == 0
    assert (k / "vclk_ff.sdc").read_text().splitlines()[-1] == "set_clock_latency -source 202.5 [get_clocks vclk]"
    hook = (k / "bind_ff_eco.tcl").read_text()
    assert "set_clock_latency" not in hook and "hold_pad_hb4.tcl" in hook and "r10_hold_pass2_hook.tcl" in hook
    v = M.mk_vars((k / "config.mk").read_text())
    assert v["CORNERS"] == "tc BC" and v["OT_HOLD_MM"] == "1" and v["OT_MM_SETUP_CORNER"] == "tc"
    assert v["OT_MM_FF_SDC"] == "/work/vclk_ff.sdc" and v["PRE_GLOBAL_ROUTE_TCL"] == "/work/bind_ff_eco.tcl"
    rec = json.loads((k / "eco_modes.json").read_text())
    assert rec["ff_bound_ps"] == 202.5 and rec["kit_mm"] is False and len(rec["dropped"]) == 1


def test_mm_rebuild_kit(tmp_path):
    k = kit(tmp_path, cfg=CFG_MM, vff="202.5")
    assert M.main([str(k)]) == 0
    hook = (k / "bind_ff_eco.tcl").read_text()
    assert "head_grt_drv_unscaled" not in hook and "set_clock_latency" not in hook
    assert json.loads((k / "eco_modes.json").read_text())["kit_mm"] is True


@pytest.mark.parametrize("case", [
    "cfg_ff_vs_lint", "cfg_tt_vs_lint", "signoff_bound", "hook_latency", "stale_vclk_ff", "no_hb4",
    "other_latency", "tt_contract", "mm_wrong_corners", "ff_sdc_elsewhere", "restaged"])
def test_fail_closed(tmp_path, case, capsys):
    kw, args = {}, []
    if case == "cfg_ff_vs_lint":
        kw["cfg"] = CFG_SINGLE.replace("OT_VCLK_FF = 202.5", "OT_VCLK_FF = 170")
    elif case == "cfg_tt_vs_lint":
        kw["lint"] = {"insertion_ps": 230.0, "insertion_ff_ps": 202.5}
    elif case == "signoff_bound":
        args = ["--ff-bound-ps", "210"]
    elif case == "hook_latency":
        kw["hook"] = HOOK.replace("-source 202.5", "-source 250")
    elif case == "stale_vclk_ff":                       # elemB R14 kit carried a stale vclk_ff.sdc 170
        kw.update(cfg=CFG_MM, vff="170")
    elif case == "no_hb4":
        kw["hook"] = HOOK.replace("source /work/hold_pad_hb4.tcl\n", "")
    elif case == "other_latency":
        kw["hook"] = HOOK + "set_clock_latency 30 [get_clocks clk]\n"
    elif case == "tt_contract":                         # a TT scene carrying the FF latency
        kw["sdc"] = SDC.replace("-source 250.0000", "-source 202.5")
    elif case == "mm_wrong_corners":
        kw["cfg"] = CFG_MM.replace("override export CORNERS = tc BC", "override export CORNERS = tc bc")
    elif case == "ff_sdc_elsewhere":
        kw["cfg"] = CFG_MM.replace("/work/vclk_ff.sdc", "/work/signoff/ff.sdc")
    elif case == "restaged":
        kw["cfg"] = CFG_SINGLE + M.MARK + " old\n"
    k = kit(tmp_path, **kw)
    before = {p.name: p.read_text() for p in k.iterdir()}
    assert M.main([str(k), *args]) == 2
    assert "HEAD_ECO_MODES FAIL" in capsys.readouterr().out
    assert {p.name: p.read_text() for p in k.iterdir()} == before      # nothing written


def test_chain_scripts_are_per_mode():
    sh = (ROOT / "tools/s81_head/head_post_route_eco.sh").read_text()
    tcl = (ROOT / "tools/s81_head/head_eco_post.tcl").read_text()
    assert '"CORNERS=tc bc"' not in sh and "--ff-bound-ps 202.5" not in sh
    assert "head_eco_modes.py" in sh and "orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts" in sh
    assert '--ff-bound-ps "$FFB"' in sh
    code = [ln for ln in tcl.splitlines() if not ln.lstrip().startswith("#")]
    body = "\n".join(code)
    assert "set_clock_latency" not in body
    assert body.index("ot_mm_sync") < body.index("read_spef") < body.index("ot_hold_structural_gate") \
        < body.index("source /work/eco_route.tcl") < body.index("ot_mm_unsync")
