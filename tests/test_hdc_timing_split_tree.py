import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from hdc_timing import K, split_tree_levels  # noqa: E402


@pytest.mark.parametrize("groups,levels", [(1, 0), (4, 2), (4096, 12), (6144, 13), (8192, 13)])
def test_levels_match_rtl_clog2(groups, levels):
    assert split_tree_levels(groups) == levels


def test_o4_non_power_of_two_exposes_one_more_tree_level():
    assert (split_tree_levels(6144) - split_tree_levels(4096)) * K["me_tree"] == 4
