"""RETRY-GUIDE: GPL-0305 on a kit with region guides is an uncharged INFRA relaunch without guides (QC slw_st_b_v1__cle6023ec2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as W  # noqa: E402

GUIDED = """OT_REGION_GUIDE ot_rg_1_4 cells 247 area 72.2 um2 box 169.96 782.08 188.37 800.49 fixed 1 fill 0.216
[ERROR GPL-0305] RePlAce diverged during gradient descent calculation, resulting in an invalid step length (Inf or NaN).
Error: global_place.tcl, 69 GPL-0305
"""
PLAIN = """[ERROR GPL-0305] RePlAce diverged during gradient descent calculation, resulting in an invalid step length (Inf or NaN).
Error: global_place.tcl, 69 GPL-0305
"""


def test_gpl0305_with_guides_is_infra_retry_guide_not_a_design_fail():
    cls, why = W.classify("place", GUIDED)
    assert cls == "INFRA" and why.startswith("RETRY-GUIDE") and "GPL-0305" in why


def test_gpl0305_without_guides_stays_a_plain_tool_error():
    cls, why = W.classify("place", PLAIN)
    assert cls == "FLOW" and "tool / Tcl error" in why


def test_only_the_place_stage_and_only_gpl0305_count():
    cls, why = W.classify("gen", GUIDED)
    assert not (cls == "INFRA" and "RETRY-GUIDE" in why)
    assert W.guide_divergence_hit("OT_REGION_GUIDE x\nGPL-0301 utilization 289 %") is None
    assert W.guide_divergence_hit("") is None


def test_an_infra_relaunch_gets_no_region_guide():
    prev = {"status": "FAIL", "stage": "geom", "class": "INFRA", "evidence": "epyc9:/x/geom/auto_geom.json"}
    assert W.region_guide_geom(prev, "epyc9") is None
