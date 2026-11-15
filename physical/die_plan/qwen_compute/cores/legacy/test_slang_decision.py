"""KIT-OPS-5 11-14: slang only up to SLANG_MAX_CELLS synth cells, except where a 1-bit bus pin needs it."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_qc as G  # noqa: E402

BIG, SMALL = 57833, 7916


def test_no_slang_recipe_is_unchanged():
    assert G.slang_decision({}, ["a[0]"], BIG) == (False, "")


def test_unknown_size_keeps_slang():
    assert G.slang_decision({"slang": True}, ["a[0]", "a[1]"], None) == (True, "")


def test_small_kit_keeps_slang():
    assert G.slang_decision({"slang": True}, ["a[0]"], SMALL) == (True, "")


def test_big_kit_drops_slang():
    use, note = G.slang_decision({"slang": True}, ["a[0]", "a[1]", "b"], BIG)
    assert not use and "SLANG_DROPPED" in note and "57833" in note


def test_big_kit_with_one_bit_bus_stays_on_slang_and_is_listed():
    use, note = G.slang_decision({"slang": True}, ["ck[0]", "d[0]", "d[1]", "rst"], BIG)
    assert use and "SLANG_KEPT" in note and "ck" in note and "d," not in note


def test_recipe_estimate_wins_over_measurement():
    assert G.slang_decision({"slang": True, "est_synth_cells": 30000}, ["a"], SMALL)[0] is False


def test_one_bit_buses():
    assert G.one_bit_buses(["ck[0]", "d[0]", "d[1]", "x", "y[3]"]) == ["ck"]
