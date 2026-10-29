import importlib.util,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import fixed_tree_provider as F

def original(*args):return ['legacy']

def test_actual_m1_chain_uses_top_horizontal_and_m7_vertical_only():
    p=F.provider_join('M9',(10.,20.),'M1',(11.109,20.236),False,original)
    assert p[-1]==('M1',11.109,20.236)
    for a,b in zip(p,p[1:]):
        if a[0]!=b[0]:assert abs(int(a[0][1:])-int(b[0][1:]))==1 and a[1:]==b[1:]
        elif a[1:]!=b[1:]:assert a[0]=='M8' and a[2]==b[2] or a[0]=='M7' and a[1]==b[1]
    assert ('M7',11.109,20.236) in p

def test_existing_m7_endpoints_are_unmodified():
    assert F.provider_join('M8',(1,2),'M7',(1,3),False,original)==['legacy']

def test_changed_base_adapter_fails_before_build():
    with pytest.raises(ValueError,match='anchor changed'):F.adapted_source('def main():pass')


def test_m3_jog_keeps_native_m1_endpoint_and_upper_column_separate():
    p=F.provider_join('M8',(10.,20.),'M1',(11.109,20.364),False,original,(11.109,20.236))
    assert ('M3',11.109,20.364) in p and ('M3',11.109,20.236) in p
    assert p[-1]==('M1',11.109,20.236)


def test_parent_stub_is_explicit_without_growing_native_pin():
    ep=dict(inst='phy',pin='clk',net='ck_n1',layer='M7',xy=[1.,1.],rect_um=[.984,.8,1.016,1.2])
    stub=dict(port='phy_clk',inst='phy',pin='clk',net='ck_n1',rect_um=list(ep['rect_um']),entry_xy_um=[1.,1.32],m7_stub_um=[.984,.8,1.016,1.347])
    plan,ss=F.native_access({'phy_clk':ep},{'records':[]},{'status':'PASS_GEOMETRY','failures':[],'stubs':[stub]})
    assert ep['rect_um']==[.984,.8,1.016,1.2] and ss['phy_clk']['m7_stub_um'][3]>ep['rect_um'][3]
    stub['rect_um']=[.984,.8,1.016,1.5]
    with pytest.raises(ValueError,match='pin geometry changed'):F.native_access({'phy_clk':ep},{'records':[]},{'status':'PASS_GEOMETRY','failures':[],'stubs':[stub]})
