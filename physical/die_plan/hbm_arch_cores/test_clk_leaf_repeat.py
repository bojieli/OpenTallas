"""HBM-CTS-LEAFSLEW (DIE-HBM-59 11-03): default-on POST_CTS clock level/leaf repeater hook, first in the POST_CTS chain."""
import importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coregen_clr", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)
sys.path.insert(0, str(HERE))
import clk_leaf_resume  # noqa: E402
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import core_infra  # noqa: E402


def eff(cfg, name):
    return coregen._effective_hook(cfg, name)


def test_hook_first_in_chain(tmp_path):
    cfg = ["export POST_CTS_TCL = /work/tap_balance.tcl", "override export POST_CTS_TCL = /work/f4_chain_leaf.tcl",
           "export OT_F4_NEXT_TCL = /work/tap_balance.tcl"]
    r = coregen.clk_leaf_repeat_hook(tmp_path, cfg)
    assert r["installed"] and r["previous_post_cts"] == "/work/f4_chain_leaf.tcl"
    assert eff(cfg, "POST_CTS_TCL") == "/work/clk_leaf_repeat.tcl"
    assert "export OT_CLR_NEXT_TCL = /work/f4_chain_leaf.tcl" in cfg
    assert eff(cfg, "OT_F4_NEXT_TCL") == "/work/tap_balance.tcl"      # rest of the chain unchanged
    assert (tmp_path / "clk_leaf_repeat.tcl").read_text() == (HERE / "clk_leaf_repeat.tcl").read_text()


def test_setup_hook_chains_after(tmp_path):
    cfg = ["export POST_CTS_TCL = /work/tap_balance.tcl"]
    coregen.clk_leaf_repeat_hook(tmp_path, cfg)
    coregen.post_cts_setup_hook(tmp_path, cfg)
    assert eff(cfg, "POST_CTS_TCL") == "/work/post_cts_setup.tcl"
    assert "source {/work/clk_leaf_repeat.tcl}" in (tmp_path / "post_cts_setup.tcl").read_text()


def test_plan_tree_skipped(tmp_path):
    (tmp_path / "core_infra_plan.json").write_text(json.dumps({"core_tree": {"clock_port": "clk"}}))
    cfg = ["export POST_CTS_TCL = /work/tap_balance.tcl"]
    r = coregen.clk_leaf_repeat_hook(tmp_path, cfg)
    assert r["installed"] is False and cfg == ["export POST_CTS_TCL = /work/tap_balance.tcl"]
    assert not (tmp_path / "clk_leaf_repeat.tcl").exists()
    assert "clk_leaf_repeat.tcl" in core_infra.PLAN_TREE_CLOCK_EDITORS


def test_resume_existing_kit_idempotent(tmp_path):
    (tmp_path / "config.mk").write_text("override export POST_CTS_TCL = /work/f4_chain_leaf.tcl\n"
                                        "export OT_F4_NEXT_TCL = /work/tap_balance.tcl\n"
                                        "override export POST_CTS_TCL = /work/post_cts_setup.tcl\n")
    r = clk_leaf_resume.apply(tmp_path, max_um=40)
    txt = (tmp_path / "config.mk").read_text()
    assert r["previous_post_cts"] == "/work/post_cts_setup.tcl"
    assert eff(txt.splitlines(), "POST_CTS_TCL") == "/work/clk_leaf_repeat.tcl"
    assert "export OT_CLR_NEXT_TCL = /work/post_cts_setup.tcl" in txt and "export OT_CLK_LEAF_MAX_UM = 40" in txt
    clk_leaf_resume.apply(tmp_path)
    assert (tmp_path / "config.mk").read_text() == txt


def test_tcl_defaults_and_off_switch():
    t = (HERE / "clk_leaf_repeat.tcl").read_text()
    assert ': 50.0}]' in t and ': 12}]' in t                     # 50 um / fanout 12 defaults
    assert 'OT_CLK_LEAF_REPEAT) ne "0"' in t                       # OT_CLK_LEAF_REPEAT=0 = old behaviour
    assert t.rstrip().endswith("{ source $::env(OT_CLR_NEXT_TCL) }")  # the chain always continues
    assert "getBTerms" in t                                        # root/port nets are never touched
