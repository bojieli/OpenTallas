"""Reject PHY meshes whose ideal seam phase cannot survive native DBU emission."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import infra_pg_domains as P
import pg_regions as G

CORE={layer:dict(layer=layer,pitch_um=8.64) for layer in ('M8','M9')}

@pytest.mark.parametrize('division',[1,3,5,9])
def test_representable_subdivision_retains_native_ground_phase(division):
    actual,rows=P.phy_grid_for_core(CORE,8.64/division)
    assert actual==division
    for row in rows:
        native=G.row_spec(row,(0,0,10000000,10000000),['VDD','VSS'])
        assert native['pitch']*division==8640
        # Ground is the second stripe, at one full PHY pitch. Every core
        # ground center is therefore exactly a PHY ground center (odd division).
        assert 8640%native['pitch']==0
        assert (8640//native['half'])%2==0

@pytest.mark.parametrize('division',[7,11,13])
def test_unrepresentable_odd_subdivision_rejected_before_native_mesh(division):
    with pytest.raises(ValueError,match='not exactly representable in DBU'):
        P.phy_grid_for_core(CORE,8.64/division)
