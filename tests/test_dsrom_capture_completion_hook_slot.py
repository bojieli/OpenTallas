import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_completion_hook_slot as H

def fixture():
    t={'VM_visible':10,'captured_credit':11,'packet_retired':11,'F':12,'later_GU0_accept':13,'SU_front_accept':19,'SU_read':20,'observed_Xtag':22,'VM_lease_release':22}
    ctx=dict(stage=0,rank=0,expert=0,phase=10,key_word=2149580800,generation=1,user=70000,xversion=1,pc=66)
    return dict(t,enrolled=True,origin_id='UNIT_FIXTURE_NOT_ACTUAL',clock_domain='native_single_clk',bank_waits_for_SU_read=False,owned_context=ctx,callback_contexts={k:dict(ctx) for k in t})

def test_source_relative_order_and_separate_leases():assert H.callback_order(fixture())
@pytest.mark.parametrize('key,value',[('captured_credit',10),('F',11),('later_GU0_accept',12),('SU_front_accept',18),('observed_Xtag',21),('VM_lease_release',21),('SU_read',18)])
def test_bad_order_rejected(key,value):
    e=fixture();e[key]=value
    with pytest.raises(ValueError):H.callback_order(e)

def test_user32_and_generation_lineage():
    e=fixture();e['callback_contexts']['F']['user']=e['owned_context']['user']&65535
    with pytest.raises(ValueError):H.callback_order(e)
    e=fixture();e['callback_contexts']['SU_read']['generation']+=1
    with pytest.raises(ValueError):H.callback_order(e)

@pytest.mark.parametrize('key,value',[('enrolled',False),('clock_domain','physical_3to4_CDC'),('bank_waits_for_SU_read',True),('SU_read',None)])
def test_missing_or_wrong_provider_rejected(key,value):
    e=fixture();e[key]=value
    with pytest.raises(ValueError):H.callback_order(e)

def test_disjoint_gross_cell_construction():
    m=H.build();cells=m['gross_hook_cells'];r=m['reservation_bbox_DBU']
    assert m['placed_body_um2']==pytest.approx(2.42028)
    assert m['additional_local_clock_reset_BUF']==2
    assert m['reserve50pct_mm2']==pytest.approx(.00000484056)
    assert all(H.E.contained(c['bbox_DBU'],r) for c in cells)
    assert all(not H.E.overlap(a['bbox_DBU'],b['bbox_DBU']) for i,a in enumerate(cells) for b in cells[i+1:])
    assert sum(c['role']=='local_CLK' for c in cells)==sum(c['role']=='local_RESETN' for c in cells)==1
    assert not m['contextual_PR_admitted'] and m['C'] is None and m['actual_callback_journal'] is None
    assert not m['SU_guard_selected'] and m['annex_charge_mm2']==0
