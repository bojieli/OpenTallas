"""KW-FIX-45 11-11 (hbm-phy-place): a hard wrapper whose single macro reaches the die edge gets a zero core margin there."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G


def hard(core, outline=(3188.16, 2073.6)):
    return {"outline_um": list(outline), "hard": True, "hard_cores": [core]}


def test_phy_spanning_macro_at_origin_gets_zero_margin_on_touched_sides():
    t = hard({"inst": "u_phy_Q", "lef": "x.lef", "origin_um": [0.0, 0.0], "outline_um": [3188.16, 1177.2]})
    assert G.kit_core_area(t) == [0.0, 0.0, 3188.16, 2073.6 - G.CORE_MARGIN_UM]


def test_non_spanning_hard_wrapper_is_unchanged():
    t = hard({"inst": "u_m", "lef": "x.lef", "origin_um": [100.0, 100.0], "outline_um": [200.0, 200.0]})
    assert G.kit_core_area(t) == [4.32, 4.32, 3188.16 - 4.32, 2073.6 - 4.32]


def test_non_hard_type_and_explicit_margins_are_unchanged():
    t = {"outline_um": [100.0, 100.0], "hard_cores": [{"inst": "u", "lef": "x.lef", "origin_um": [0.0, 0.0], "outline_um": [100.0, 100.0]}]}
    assert G.kit_core_area(t) == [4.32, 4.32, 100.0 - 4.32, 100.0 - 4.32]
    t2 = hard({"inst": "u_phy_Q", "lef": "x.lef", "origin_um": [0.0, 0.0], "outline_um": [3188.16, 1177.2]})
    t2["kit_core_margins_um"] = [4.32, 4.32, 4.32, 4.32]
    assert G.kit_core_area(t2)[0] == 4.32
