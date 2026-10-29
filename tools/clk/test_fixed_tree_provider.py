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
