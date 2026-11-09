"""FLOW-7 10-30: opt-in plan budgets.dpl_legalizer="diamond" -> gen phys exports DETAIL_PLACEMENT_ARGS =
-use_diamond_legalizer (KV-022 SD sdpg 3_4: negotiation DPL stalled at 902 illegal cells around 12308 FIRM landing
cells; diamond legalised in 44 s). Absent key = no line (kits unchanged); any other value fails."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402


def test_absent_key_emits_nothing():
    assert gen_phys._dpl_args({}) == []
    assert "dpl_legalizer" not in schema.DEFAULT_BUDGETS


def test_diamond_emits_the_orfs_dpl_args():
    assert gen_phys._dpl_args({"dpl_legalizer": "diamond"}) == ["export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"]


def test_other_values_fail():
    with pytest.raises(SystemExit):
        gen_phys._dpl_args({"dpl_legalizer": "negotiation"})


def test_config_mk_uses_it_once():
    src = (HERE / "gen_phys.py").read_text()
    assert src.count("*_dpl_args(P.budgets, tn, dpl_diamond, landing=") == 1
    assert src.count("DETAIL_PLACEMENT_ARGS") == 3          # helper (2 return lines) + docstring; no other writer


def test_per_type_opt_in():
    b = {"dpl_legalizer_types": ["kv3_io_cor"]}
    assert gen_phys._dpl_args(b) == []
    assert gen_phys._dpl_args(b, "kv3_io_cor") == ["export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"]
    assert gen_phys._dpl_args(b, "kv3_io_cor__cl1234") == ["export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer"]
    assert gen_phys._dpl_args(b, "kv3_io_cor_v1") == []
    assert "dpl_legalizer_types" not in schema.DEFAULT_BUDGETS


def test_release_grown_hook_follows_the_refirm():
    src = (HERE / "gen_phys.py").read_text()
    assert src.count("+ CLAND_RELEASE_GROWN_TCL)") == 1
    t = gen_phys.CLAND_RELEASE_GROWN_TCL
    assert "u_cland_" in t and "setPlacementStatus PLACED" in t and "TAPCELL" not in t


# DIE-QC-66/PLAN 11-03 DPL class: landing-band kits default to diamond DPL with a whole-kit search window
WIN = "export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer -max_displacement {618 1335}"


def test_landing_kit_defaults_to_diamond_whole_kit_window():
    assert gen_phys._dpl_args({}, "slw_st_b_v2", landing=True, outline=[617.76, 1334.88]) == [WIN]
    assert gen_phys._dpl_args({}, "slw_st_b_v2", landing=False, outline=[617.76, 1334.88]) == []   # no FIRM bands: unchanged


def test_every_kit_diamond_call_gets_the_window():
    o = [617.76, 1334.88]
    assert gen_phys._dpl_args({"dpl_legalizer": "diamond"}, "x", outline=o) == [WIN]
    assert gen_phys._dpl_args({"dpl_legalizer_types": ["x"]}, "x__cl1", outline=o) == [WIN]
    assert gen_phys._dpl_args({}, "x", diamond=True, outline=o) == [WIN]


def test_off_types_keep_orfs_default():
    b = {"dpl_legalizer_off_types": ["coll_n"]}
    assert gen_phys._dpl_args(b, "coll_n", landing=True, outline=[1, 1]) == []
    assert gen_phys._dpl_args(b, "coll_n__cl9", landing=True, outline=[1, 1]) == []
    assert gen_phys._dpl_args(b, "coll_s", landing=True, outline=[1, 1]) != []
    assert "dpl_legalizer_off_types" not in schema.DEFAULT_BUDGETS
    assert "dpl_legalizer_off_types" in (HERE / "die_plan.schema.json").read_text()


def test_ft_reserved_type_gets_diamond():
    # DIE-HBM-97 11-09: write_type_kit passes landing=... or bool(ft_reservation)
    src = (Path(__file__).with_name("gen_phys.py")).read_text()
    assert 'or bool(ft_reservation), outline=t["outline_um"])' in src
    assert gen_phys._dpl_args({}, "q_b100__physical_v1", landing=True, outline=(708.48, 1555.2)) == [
        "export DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer -max_displacement {709 1556}"]
    assert gen_phys._dpl_args({"dpl_legalizer_off_types": ["q_b100"]}, "q_b100__physical_v1", landing=True) == []
