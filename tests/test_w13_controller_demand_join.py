import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_controller_demand_join import join


def q(i,die=0,partial=True,stack=2):
    return {'id':str(i),'position':0,'die':die,'stack':stack,'physical_stack':die*4+stack,
        'PC':0,'sector':0,'instruction':5,'byte_mask':0x10001 if partial else (1<<32)-1,
        'RMW_required':partial,'producer_instructions':[3,4],'fence_instruction':6,
        'read_instruction':7,'scores_instruction':8,'pv_instruction':9}


def test_partial_costs_locked_read_plus_fullwrite_and_one_visible_ACK():
    d=join([q(0),q(1,partial=False)])
    assert d['combined_READ_WR_commands']==3 and d['combined_port_bytes']==96
    assert d['WR_visible_ACK_obligations']==2 and d['locked_RMW_READ_obligations']==1
    assert d['provider_admission_trial']['calendar'] is None


def test_die_and_PC_ownership_and_actual_stack_skew_preserved():
    d=join([q(0,stack=0),q(1,die=1,partial=False,stack=2)])
    assert [(s['die'],s['stack'],s['port_bytes']) for s in d['per_position_die_stack']]==[(0,0,64),(1,2,32)]
    b=q(0);b['PC']=1
    with pytest.raises(ValueError,match='PC mapping'):join([b])
    b=q(0);b['physical_stack']=7
    with pytest.raises(ValueError,match='stack identity'):join([b])
