"""HBM core kits legalise with the diamond DPL by default (DIE-HBM-100 11-11; ot_svgr_top DPL-0701 + detail_place.tcl bad optional access)."""
import importlib.util
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coregen_dpl", HERE / "gen_core_kit_hbm.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def test_default_is_diamond():
    assert G.dpl_cfg_lines("diamond", []) == ["export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"]
    assert G.dpl_cfg_lines("diamond", ["OT_HOLD_REPAIR_SCOPE=reg2reg"]) == ["export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"]


def test_item_opt_out_keeps_orfs_default():
    assert G.dpl_cfg_lines("default", []) == []


def test_orfs_var_override_wins_without_a_second_line():
    assert G.dpl_cfg_lines("diamond", ["DETAIL_PLACEMENT_ARGS=-use_diamond_legalizer -max_displacement {303 640}"]) == []


def test_bad_mode_refused():
    with pytest.raises(SystemExit):
        G.dpl_cfg_lines("negotiation", [])


def test_argument_default_and_config_line_order():
    src = (HERE / "gen_core_kit_hbm.py").read_text()
    assert "--dpl-legalizer\", choices=[\"diamond\", \"default\"], default=\"diamond\"" in src
    assert src.index("cfg += dpl_cfg_lines(") < src.index("for kv in a.orfs_var]")      # --orfs-var stays last and wins
