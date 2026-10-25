"""Placed macro contents are obstacles to clock taps, like reset relays."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import schema as S

def test_clock_tap_avoids_sys_c_phy_content():
    t=dict(outline_um=[2160,1036.8],contents=[dict(inst="u_phy",lef="phy.lef",origin_um=[691.2,17.28],outline_um=[777.6,777.6])])
    x,y=S.tap_clear(t,1080,518.4)
    assert not 682.56<x<1477.44 or not 8.64<y<803.52

def test_clock_tap_honours_rotated_content_footprint():
    t=dict(outline_um=[500,500],contents=[dict(inst="u_sram",lef="sram.lef",origin_um=[100,100],outline_um=[40,200],orient="R90")])
    x,y=S.tap_clear(t,250,120)
    assert not 91.36<x<308.64 or not 91.36<y<148.64

def test_unplaced_or_logic_contents_preserve_old_clock_taps():
    t=dict(outline_um=[500,500],contents=[dict(inst="logic",origin_um=[100,100],outline_um=[200,200]),dict(inst="planned",lef="planned.lef")])
    assert S.tap_clear(t,250,250)==(250,250)
