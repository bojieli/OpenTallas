"""FLOW-7 10-30: plan budgets.dpl_legalizer="diamond" -> gen phys exports DETAIL_PLACEMENT_ARGS =
-use_diamond_legalizer (KV-022 SD sdpg 3_4: negotiation DPL stalled at 902 illegal cells around 12308 FIRM landing
cells; diamond legalised in 44 s). AUTOBUILD-PIPE-5 10-31 (OWNER 12.27): DEFAULT-ON (absent key = diamond);
"negotiation" = explicit opt-out (no line); any other value fails."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402


def test_absent_key_is_diamond_default_on():
    assert gen_phys._dpl_args({}) == ["export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"]
    assert "dpl_legalizer" not in schema.DEFAULT_BUDGETS


def test_negotiation_is_the_explicit_opt_out():
    assert gen_phys._dpl_args({"dpl_legalizer": "negotiation"}) == []


def test_diamond_emits_the_orfs_dpl_args():
    assert gen_phys._dpl_args({"dpl_legalizer": "diamond"}) == ["export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"]


def test_other_values_fail():
    with pytest.raises(SystemExit):
        gen_phys._dpl_args({"dpl_legalizer": "tetris"})


def test_config_mk_uses_it_once():
    src = (HERE / "gen_phys.py").read_text()
    assert src.count("*_dpl_args(P.budgets),") == 1
    assert src.count("DETAIL_PLACEMENT_ARGS") == 2          # helper + docstring; no other writer of the ORFS var
