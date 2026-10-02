import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_v1_expanded_service as E

@pytest.fixture(scope='module')
def model():return E.build()

@pytest.mark.parametrize('name',['Qwen','DeepSeek'])
def test_complete_die_reservations(model,name):
    m=model['models'][name]
    assert m['SMs_per_die']==32 and len(m['SM_placements'])==32
    assert m['full_die_geometry_screen_pass'] and not m['full_die_obstacle_conflicts']
    assert not m['corridor_obstacle_conflicts']
    assert m['area']['complete_reserved_occupancy_mm2']<m['area']['die_mm2']
    assert len(m['global_service_cuts'])==32*209
    assert m['global_service_cut_screens_pass']
    assert not m['outside_die'] and not m['SM_pair_conflicts']
    assert [sum(t['stack']==s for t in m['SM_placements'])for s in range(4)]==[8]*4
    for tile in m['SM_placements']:
        x,y=tile['service_origin_um'];service=E.rect(x,y,m['service']['width_um'],m['service']['height_um'])
        assert E.contained(service,tile['bbox_um'])
        assert not E.overlap(service,tile['retained_actual_body_bbox_um'])

@pytest.mark.parametrize('name',['Qwen','DeepSeek'])
def test_rf_bank_port_and_lane_binding(model,name):
    s=model['models'][name]['service'];rf=[m for m in s['macro_placements']if m['name'].startswith('RF.')]
    assert len(rf)==128 and len(s['macro_placements'])==130
    assert len({m['name']for m in rf})==128
    assert all(m['physical_read_ports']==1 and m['physical_write_ports']==1 for m in rf)
    assert sum(l['H1_SIMD_lanes']for l in s['logic_slots'])==128
    assert sum(l['V1_lanes']for l in s['logic_slots'])==32
    assert all(l['capacity_footprint_um2']>=l['required_footprint_um2']for l in s['logic_slots'])
    assert not s['all_service_macro_logic_conflicts']

@pytest.mark.parametrize('name',['Qwen','DeepSeek'])
def test_distributed_cuts_include_c0_and_pg(model,name):
    m=model['models'][name];s=m['service']
    assert len(s['bank_cuts'])==16*13 and len(s['C0_cuts'])==1 and len(m['corridor_cuts'])==(10 if name=='Qwen' else 14)
    for c in s['bank_cuts']+s['C0_cuts']+m['corridor_cuts']:
        assert c['screen_pass'] and c['margin_tracks']>=0
        assert all(l['signal_tracks']+l['PG_clock_via_reserved_tracks']==l['raw_tracks'] for l in c['layers'].values())
        assert all(l['PG_clock_via_reserved_tracks']>=l['signal_tracks']for l in c['layers'].values())
        assert not c['actual_new_PDN_bound']
    assert {c['owner']for c in s['bank_cuts']}=={f'bank{b}/{d}cut'for b in range(16)for d in ['X','Y']}
    assert s['bank_cuts'][0]['demand_tracks']>=2048+256+1152

@pytest.mark.parametrize('name,count,ffs',[('Qwen',368,185341),('DeepSeek',608,77192)])
def test_retained_actual_exclusions_and_unknown_ff(model,name,count,ffs):
    m=model['models'][name];a=m['actual_source_geometry']
    assert len(m['retained_native_cuts'])==count
    assert a['actual_FFs']==ffs and a['actual_FFs_placed']==0
    assert a['retained_PDN_shapes']>a['unknown_layer_vias_blocked_on_all_planes']>0
    for c in m['retained_native_cuts']:
        assert c['policy50pct_signal_tracks']==c['free_tracks']//2
    assert not m['hardware_admitted']
    assert any('FFs unplaced' in b for b in m['blockers'])

@pytest.mark.parametrize('name',['Qwen','DeepSeek'])
def test_transport_registers_are_not_free(model,name):
    m=model['models'][name];s=m['service'];a=m['area']
    assert s['transport_pipeline_hops']==5
    assert s['extra_register_bits_proposed']==16*(512+128+64)*2*5
    assert s['bank_pipeline_bits_each']==4*(512+128+64)*2
    assert a['transport_state_incremental_footprint_um2']>a['central_endpoint_footprint_um2']>0
    assert a['central_endpoint_footprint_um2']<=a['C0_strip_spare_before_transport_um2']
    assert a['interSM_trunk_register_footprint_um2']>0
    assert all(p['command_credit']==1 and p['register_bits']>0 for p in m['trunk_pipeline_reservations'])
    assert m['latency']['request_hops']==m['latency']['return_hops']==5
    assert len(m['latency']['PC_distance_costs'])==(1737 if name=='Qwen' else 2213)
    assert m['latency']['whole_token_ns']is None and not m['latency']['SSFF_qualified']

def test_serialized_distance_counts():
    x=E.latency_delta(3,2,outward_hops=5,return_hops=5)
    assert x['added_ticks']==50
    assert not x['RF_baseline_recharged'] and not x['I64_RMW_recharged'] and not x['C0_front_recharged']

@pytest.mark.parametrize('kwargs',[dict(read_pairs=-1,writes=1,outward_hops=1,return_hops=1),dict(read_pairs=1,writes=1,outward_hops=1,return_hops=1,hop_ticks=0),dict(read_pairs=1,writes=1,outward_hops=1.5,return_hops=1)])
def test_invalid_cost_rejects(kwargs):
    with pytest.raises(ValueError):E.latency_delta(**kwargs)

def test_actual_grid_deduplicates_and_reserves():
    grid=json.loads((E.INPUT/'DS_grid.json').read_text())
    c=E.track_capacity(grid,'X',0,450,['M7','M9'])
    assert c['M7']['raw_tracks']==7032 and c['M9']['raw_tracks']==5624
    assert sum(x['signal_tracks']for x in c.values())==6328

def test_qwen_rf_abstract_not_qualified(model):
    assert 'not transferred' in model['models']['Qwen']['service']['RF_abstract_provider']
    assert not model['hardware_admitted'] and model['no_RTL_or_PnR']


@pytest.mark.parametrize('bits',[32,64])
def test_atomic_all_bank_owner(bits):
    f=E.ProviderAtomicFence(rank=1,SM=31,generation=5,response_stall_bound=2)
    t=(5,1736,1,1,31);reads=list(range(3 if bits==32 else 5));writes=[510] if bits==32 else [510,511]
    f.accept(t,reads,writes)
    while f.owner.phase=='reading':
        f.read(t)
        for bank in range(15):f.bank_return(t,bank)
        with pytest.raises(ValueError):f.complete(t,native_ticks=1)
        assert not f.unrelated_request_ready()
        with pytest.raises(ValueError):f.bank_return(t,0)
        f.bank_return(t,15)
    f.complete(t,native_ticks=1)
    for addr in writes:
        assert f.write(t)==addr
        for bank in range(16):f.bank_ACK(t,bank,0)
        for bank in range(15):f.bank_ACK(t,bank,1)
        with pytest.raises(ValueError):f.consumer(t)
        f.bank_ACK(t,15,1)
    f.consumer(t)
    assert not f.unrelated_request_ready()
    f.retire(t,reverse_grant=True)
    assert f.unrelated_request_ready()

@pytest.mark.parametrize('bank',[-1,16,1.5])
def test_atomic_invalid_bank_retains_credit(bank):
    f=E.ProviderAtomicFence(rank=0,SM=0,generation=1,response_stall_bound=1);t=(1,0,1,0,0)
    f.accept(t,[0],[1]);f.read(t)
    with pytest.raises(ValueError):f.bank_return(t,bank)
    assert f.mask==0 and not f.unrelated_request_ready()

def test_atomic_generation_rejection():
    f=E.ProviderAtomicFence(rank=0,SM=0,generation=1,response_stall_bound=1);t=(1,0,1,0,0)
    f.accept(t,[0],[1]);f.read(t)
    with pytest.raises(ValueError):f.bank_return((2,0,1,0,0),0)
    assert f.mask==0


def test_qwen_private_routes_reserved_and_repriced(model):
    q=model['models']['Qwen']
    assert len(q['Qwen_private_provider_routes'])==12
    assert len(q['Qwen_private_provider_cuts'])==12 and all(c['screen_pass']for c in q['Qwen_private_provider_cuts'])
    assert q['area']['Qwen_private_pipeline_footprint_um2']>0
    assert q['latency']['sizing_loaded_wire_upper_ps_per_um']==.81
    assert q['latency']['nominal_request_hops']==4
    assert any(c.get('private_provider_reserved_height_um',0)==120.96 for c in q['corridor_cuts'])
    assert not q['full_die_obstacle_conflicts'] and not q['corridor_obstacle_conflicts']
    for t in q['SM_placements']:
        assert all(not E.overlap(t['bbox_um'],p['bbox_um'])for p in q['Qwen_private_provider_routes'])


@pytest.mark.parametrize('vector,lane,copy',[(0,0,0),(127,7,1),(128,8,0),(255,127,1),(256,0,0),(383,8,1),(384,7,0),(511,127,1)])
def test_actual_rf_boundary_decomposition(vector,lane,copy):
    x=E.provider_location(vector,lane,copy)
    assert x['page']*128+x['row']==vector
    assert x['bank']*8+x['word']==lane
    assert x['macro']==f"RF.b{x['bank']}.p{x['page']}.copy{copy}"
    assert x['bit_offset']==x['word']*32

@pytest.mark.parametrize('address',[(512,0,0),(0,128,0),(0,0,2),(-1,0,0)])
def test_non_rf_home_rejected(address):
    with pytest.raises(ValueError):E.provider_location(*address)
