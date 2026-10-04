import copy
import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/dsrom_selected_kv_capture_ledger.py'
s=importlib.util.spec_from_file_location('ledger',P);M=importlib.util.module_from_spec(s);s.loader.exec_module(M)

def rows():return [dict(die=s*4+r,stage=s,rank=r,stacks=1,batch=216,context=1048576,state_bytes_per_user=93458432,other_live_bytes=0,usable_bytes_per_stack=20250000000) for s in range(81) for r in range(4)]

def test_selected_nodes_are_sized_to_active_pairs_not4096():
    r=M.model();n=r['return_inventory']
    assert n['nodes']==4706 and n['RD']==64 and n['ROOTD']==128
    assert n['existing_FF50_storage_reservation_mm2']==pytest.approx(31.548,abs=.0005)
    assert not n['area_delta_applied'] and not r['physical_launch_allowed']
    assert r['selected_KV_capacity'] is None and r['KV_stack_count_adopted'] is None

def test_finite_capture_read_write_and_stagewidth_are_not_conflated():
    s=M.model()['finite_capture']['0']
    assert s['independent_write_ports']==128 and s['write_bits_per_edge']==8832
    assert s['scalar_read_records_per_edge']==1 and s['exact_seats']==576
    assert s['historical_stage_identity_bits']==6 and s['required_selected_stage_identity_bits']==7
    assert s['replication_count'] is None and not s['selected_phase_count_bound']

def test_actual_complete_byte_capacity_and_reserve_failure():
    a=rows();assert M.selected_capacity(a)['all_fit']
    a[0]['other_live_bytes']=62978689
    assert not M.selected_capacity(a)['all_fit']

@pytest.mark.parametrize('mut',['missing','duplicate','wrong_context','wrong_batch','float_bytes'])
def test_bad_capacity_inventory_refused(mut):
    a=rows()
    if mut=='missing':a.pop()
    if mut=='duplicate':a[-1]=copy.deepcopy(a[0])
    if mut=='wrong_context':a[0]['context']=200000
    if mut=='wrong_batch':a[0]['batch']=1
    if mut=='float_bytes':a[0]['other_live_bytes']=float('nan')
    with pytest.raises(ValueError):M.selected_capacity(a)

def test_no_RD16_or_alternate_count():
    n={'parameters':{'RD':16}}
    with pytest.raises(ValueError):M.return_inventory(2417,n)
    with pytest.raises(ValueError):M.return_inventory(4096,{'parameters':{'RD':64}})
