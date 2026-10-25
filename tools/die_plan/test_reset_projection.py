"""Nearest legal reset-relay site must search through overlapping keepouts."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import reset_tree as RT

def test_hbm_ne_ep_pin_core_and_phy_halo():
    # Actual e_budget/joint_abi NE_io u_ep_N2 pin, grown core and clock-PG keepouts.
    p=(201.672,1114.579)
    boxes=[(4.32,30.24,613.008,639.36),(194.4,1110.24,453.6,1494.72),
           (-8.64,-8.64,656.64,1122.28),(4.752,-8.64,656.64,1058.64)]
    bounds=(4.32,4.32,643.68,2414.88)
    q=RT.push_off(p,boxes,bounds)
    assert RT._free(q,boxes,bounds)
    assert q==(194.39,1122.29)
    assert abs(RT._man(p,q)-14.993)<1e-6
    # Old first-free-depth choice was legal but too far for the unchanged380um planning limit.
    assert RT._man(p,(201.672,1494.73))>405-25

def test_single_box_and_already_free_unchanged():
    b=[(10,10,30,30)];bounds=(0,0,40,40)
    assert RT.push_off((2,2),b,bounds)==(2,2)
    assert RT.push_off((11,20),b,bounds)==(9.99,20)

def test_three_overlaps_do_not_stop_at_far_first_projection():
    p=(20,20);b=[(10,10,100,100),(-10,-10,110,25),(5,5,15,35)]
    bounds=(0,0,120,120);q=RT.push_off(p,b,bounds)
    assert RT._free(q,b,bounds)
    assert RT._man(p,q)<30
