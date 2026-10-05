from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_gpu_elementwise_calendar as E


def test_moe_sum_preserves_zero_first_add_and_ordered_seven_slots():
    r=E.build();p=r['recipe'];adds=[x for x in p if x['op']=='FADD']
    assert len(adds)==7 and adds[0]['src']==['@F32_POS_ZERO','v']
    assert all(x['src']==['acc','v'] for x in adds[1:])
    assert r['calendar']['cycles']>0 and len(r['source_graph_binding'])==40
    assert r['staging']['shared_bytes_with4096control']<65536
    assert not r['physical_admission'] and r['full_token_cycles'] is None


def test_two_warp_calendar_retains_finite_shared_port_cost():
    p=E.provider();r=p['calendar'](E.moe_recipe(p),2)
    assert r['shared_issue_cycles']==16
    assert r['warp_instructions']['FADD']==14
    assert r['peak_live_value_registers']+r['reserved_address_loop_registers']<=32


def test_mutant_first_add_unknown_constant_rejected():
    p=E.provider();recipe=E.moe_recipe(p);recipe[2]['src'][0]='@UNKNOWN'
    with pytest.raises(ValueError,match='unknown constant'):p['calendar'](recipe,2)
