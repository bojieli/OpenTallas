import sys,json,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_capture_timing as T
@pytest.fixture(scope='module')
def model():return T.model()
def test_table_bound_without_monotonic_assumption():
    table=dict(slew=[5,10],load=[.72,1.44],values=[[7,3],[4,6]])
    assert T.upper(table,10,1.44)==7
    assert T.upper(table,5,.72)==7
@pytest.mark.parametrize('slew,cap',[(4,.72),(5,.5),(321,1.44),(10,47)])
def test_no_subgrid_or_extrapolation(slew,cap):
    table=dict(slew=[5,10,320],load=[.72,1.44,46.08],values=[[1]*3]*3)
    with pytest.raises(ValueError):T.upper(table,slew,cap)
def test_source_cell_arcs():
    lib=T.library()
    for corner in ('SS','FF'):
        for master in (T.C.HQ,T.C.ASR,T.C.NAND,T.C.INV,T.C.BUF):
            assert len(lib[corner][master]['tables'])>=4
        assert len(lib[corner][T.C.NAND]['tables'])==8 # actual A/B arcs

def test_cut_is_not_admitted(model):
    assert model['verdict']=='FAIL_ONE_BALANCED_CUT_CONDITIONAL_SS'
    assert not model['SS_paths']['stage1_payload']['conditional_setup_screen_PASS']
    assert not model['SS_paths']['stage2_shared_root_bank_bit2']['conditional_setup_screen_PASS']
    assert not model['RTL_or_build_admitted']
    assert not model['timeout']['proposed4096_selected']
    assert model['timeout']['default1024_FAIL_preserved']

def test_omitting_control_and_feedback_creates_false_pass(model):
    bare=T.evaluate('SS',T.C.HQ,10)
    assert bare['path_and_constraints_ps']<1000/1.2
    assert max(p['path_and_constraints_ps'] for p in model['SS_paths'].values())>1000/1.2

def test_positive_loaded_stages(model):
    for corner_paths in (model['SS_paths'],model['FF_propagated_paths']):
        for p in corner_paths.values():
            for s in p['steps']:
                assert s['wire_cap_fF']>0
                assert s['wire_length_ceiling_um']>0
                assert 5<=s['input_slew_ps']<=320
                assert s['total_load_fF']>=.72
            assert p['destination_slew_ps']<=320

def test_clock_edge_identity(model):
    c=model['conditional_calendar']
    assert c['read_request_first']==c['intermediate_capture_first']==423
    assert c['final_output_postNBA_first']==424
    assert c['downstream_accept_first']==425
    assert c['downstream_accept_last']==1000
    assert c['downstream_accept_last']-c['downstream_accept_first']+1==576
    assert c['calendar_is_conditional_not_admitted']
    assert c['full_program_consumer_deadline'] is None

def test_priced_pipeline(model):
    c=model['cost']
    assert c['data_FF_bits']==33*69
    assert c['async_control_FF_bits']==39
    assert c['hold_mux_NAND2_cells']==3*(2277+39)
    assert c['extra_global_root_select_BUF']==20
    assert c['cell_body_delta_um2']>1500

def test_hold_failure_kept(model):
    assert model['FF_hold_screens']['feedback_hold_payload']['conditional_zero_wire_margin_ps']<0
    assert all(not p['physical_FF_hold'] for p in model['FF_hold_screens'].values())

def test_two_credit_pipe_held_return():
    # Independent registered edge oracle: consume OLD stage2, shift OLD
    # stage1, accept next record. A held sink freezes both stages, bounded2.
    slots=[None,None];accepted=[];delivered=[];nextrow=0
    for edge in range(423,1020):
        blocked=edge in (424,425,426)
        if blocked and slots[1] is not None:continue
        if slots[1] is not None:delivered.append((slots[1],edge))
        slots[1]=slots[0];slots[0]=None
        if nextrow<576:
            slots[0]=nextrow;accepted.append((nextrow,edge));nextrow+=1
        assert sum(x is not None for x in slots)<=2
    assert [r for r,e in delivered]==list(range(576))
    assert delivered[0]==(0,427)
    assert accepted[0]==(0,423)
