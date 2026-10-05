import itertools,json,sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_capture_cells as C
@pytest.fixture(scope='module')
def model(): return C.model()
@pytest.mark.parametrize('a,b,s',list(itertools.product([False,True],repeat=3)))
def test_allowed_nand_mux(a,b,s): assert C.mux(a,b,s)==(b if s else a)
def test_cells_and_polarity(model):
    assert model['reset']['HQ_QN_restored_with_INV']
    assert model['reset']['control_async_RESETN']
    for cell in model['source_cell_facts']:
        for corner in ['SS','FF']:
            assert model['source_cell_facts'][cell][corner]['area_um2']>0
    assert model['total_cell_counts'][C.HQ]==39744
    assert model['total_cell_counts'][C.ASR]==1483
    assert model['SETN_TIEHI_cells']==1483
@pytest.mark.parametrize('n',[8,69,128,1483,41227])
def test_tree_positive_and_bounded(n):
    levels=C.tree(n);previous=n
    for level in levels: assert level*8>=previous;previous=level
    assert levels[-1]==1

def test_source_invariant_mutant():
    plans,_=C.B.allocation();plans=copy.deepcopy(plans);plans[0]['rows'][0]=1
    with pytest.raises(ValueError): C.invariant(plans)
def test_ports_and_slot(model):
    a,b=model['raw_record_slot_templates'];assert a['seats']==320 and b['seats']==256
    assert a['width_um']==b['width_um'];assert a['height_um']>b['height_um']
    assert model['mux']['maximum_mux_levels']==10
    assert model['mux']['one_edge_timing_qualified'] is False
    assert model['physical_variant']=='exact576 FF seats; no640padding selected'
    assert model['missing_deadline_is_not_zero']
    assert model['slot_and_provider_deadline_from_Hubble'] is None
    assert not model['timeout4096_selected']
    assert not model['new_RTL_or_build']
def test_area_conservation(model):
    total=sum(model['cell_body_area_by_section_um2'].values())+model['SETN_TIEHI_LEF_area_um2']
    assert abs(total-model['subtotal_body_area_um2'])<1e-7
    assert model['subtotal_core_reservation_at50pct_um2']==2*total

def test_pins():
    assert len(C.pinned())>=6
    assert all(len(v)==64 for v in C.pinned().values())
