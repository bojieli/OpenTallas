"""Explicit guide contracts prevent malformed or out-of-frame placement inputs."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_core_kit_hbm as G


def test_valid_existing_stage_region():
    g=dict(name='leaf0_capture',prefixes=['u_fcore.g_leaf[0].u_leaf.captured'],box_um=[107.46,80,133.38,250])
    assert G.register_guides_spec([g],(648,820.8))==[g]
    assert G.register_guides_spec([],(648,820.8))==[]


def test_reject_ambiguous_or_unsafe_regions():
    g=dict(name='leaf0',prefixes=['u.captured'],box_um=[10,10,30,40])
    cases=[[g,g],[dict(g,box_um=[10,10,650,40])],[dict(g,prefixes=[])],
           [dict(g,name='leaf;error')],[dict(g,prefixes=['a} [error x]'])]]
    for guides in cases:
        try:G.register_guides_spec(guides,(648,820.8))
        except ValueError:pass
        else:raise AssertionError('invalid register guide accepted')
