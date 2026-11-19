"""CBC-RULES-1119 11-19: rule 2 by wire class (leg_class.py) and the tap-region rule constants."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbc_rules as RULES
import leg_class as LC


def test_constants():
    assert RULES.REACH_CORE_SPAN_UM == 200.0 and RULES.REACH_BUFFERED_UM == 550.0
    assert RULES.TAP_REGION_WH_UM == 300.0 and RULES.TAP_SPILL is False and RULES.TAP_MAX_SINKS == 1000


def test_core_span_takes_the_cheaper_bend():
    rects = [(100, -10, 400, 10)]                         # a core across y = 0 from x 100 to 400
    assert LC.core_span_um((0, 0), (500, 0), rects) == 300
    assert LC.core_span_um((0, 0), (500, 50), rects) == 0     # y first, then x along y = 50: clear of the core


def test_classify():
    assert LC.classify(540, 0) == ("buffered", 1)             # col_h9_r2 class: closes with repair, no cycle
    assert LC.classify(1190, 0) == ("buffered", 3)            # 1.19 mm pure: 2 stations, not 4
    assert LC.classify(540, 250) == ("core", 2)               # over a core: +1
    assert LC.classify(540, 0, logic=True) == ("logic", 2)
    assert LC.classify(2000, 900, name="strap_ca_3") == ("static", 1)


def test_classify_pts_uses_shared_classify_leg():
    core = [(100.0, -50.0, 400.0, 50.0)]
    assert LC.classify_pts((0.0, 0.0), (500.0, 0.0), core)[:2] == ('core', 2)          # 300 um of core on every L path
    assert LC.classify_pts((0.0, 100.0), (500.0, 100.0), core)[:2] == ('buffered', 1)  # passes above it
    small = [(100.0, -50.0, 250.0, 50.0)]                                               # crosses only 150 um of core
    assert LC.classify_pts((0.0, 0.0), (500.0, 0.0), small)[:2] == ('buffered', 1)
    assert LC.classify_pts((0.0, 0.0), (900.0, 0.0), core, logic=True)[:2] == ('core', 3)
    assert LC.classify_pts((0.0, 0.0), (900.0, 0.0), [], launch='u_strap_tie.q')[:2] == ('static', 1)
