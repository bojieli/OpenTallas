"""region_guide boxes (QC slw_st_b_v1__cle6023ec2, GPL-0305): low fill target tied to the kit utilisation and a larger minimum side."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import region_guide as RG  # noqa: E402


def test_fill_target_follows_the_kit_utilisation_and_never_exceeds_the_default():
    assert RG.box_density(None) == RG.BOX_DENSITY == 0.20
    assert abs(RG.box_density(0.5) - 0.20) < 1e-12 and RG.box_density(0.3) == 0.4 * 0.3 and RG.box_density(0.9) == 0.20


def test_a_247_register_group_gets_a_box_well_above_the_one_that_diverged():
    area = 72.2                                          # slw_st_b ot_rg_1_4: 247 registers
    tile = (0, 0, 180, 180)
    b = RG.guide_box(tile, (90, 90), area, [])
    side = b[2] - b[0]
    assert side >= RG.BOX_MIN_SIDE and (b[2] - b[0]) * (b[3] - b[1]) >= area / RG.BOX_DENSITY - 1e-6
    assert area / ((b[2] - b[0]) * (b[3] - b[1])) <= 0.20 + 1e-9          # fill at most 0.20 (it was 0.216 at 18.4 um)


def test_a_small_group_still_gets_the_minimum_side_and_stays_inside_its_tile():
    b = RG.guide_box((0, 0, 134, 134), (3, 3), 2.0, [])
    assert b[2] - b[0] >= RG.BOX_MIN_SIDE - 1e-9 and b[0] >= 0 and b[1] >= 0
    t = RG.guide_box((0, 0, 10, 10), (5, 5), 2.0, [])          # a tile smaller than the minimum side wins (boxes stay disjoint)
    assert t[2] - t[0] <= 10 + 1e-9


def test_plan_passes_the_utilisation_to_the_box():
    src = (Path(__file__).resolve().parent / "region_guide.py").read_text()
    assert "density=box_density(target_util)" in src and "--target-util" in src
