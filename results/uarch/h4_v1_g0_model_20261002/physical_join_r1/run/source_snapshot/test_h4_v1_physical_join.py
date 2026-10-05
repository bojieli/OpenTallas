import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_v1_physical_join as J
import h4_v1_g0_model as V

@pytest.fixture
def owner():return J.SerializedOwner(rank=1,SM=31,generation=7,response_stall_bound=4)
T=(7,1736,1,1,31)

def test_actual_mapping_and_composed_cost():
    m=J.build()
    for name,n in [('Qwen',64),('DeepSeek',3072)]:
        x=m['models'][name];assert len(x['rank_to_die_SM'])==n
        assert len({r['instance'] for r in x['rank_to_die_SM']})==n
        assert all(r['rank']==r['die'] and 0<=r['SM']<32 for r in x['rank_to_die_SM'])
        s=x['slot'];assert not s['existing_slot_fits_any_bound']
        assert all(d>0 for d in s['deficit_cell_um2_range'])
        assert s['composed_logic_um2_range']==[s['H1_logic_um2']+s['C0_incremental_logic_um2']+a for a in s['V1_incremental_logic_um2_range']]
        assert not s['physical_slot_admitted'] and s['occupancy_credit_um2']==0
        assert x['routing']['V1_channels_required']==3
        assert not x['opcode_hardware_coverage'] and x['opcode_source_semantics_count']==22
    assert not m['RTL_allowed'] and not m['hardware_admitted']
    assert sum(m['RF_contract']['owner_gate_state_layout'].values())==203
    assert m['RF_contract']['owner_gate_state_bits']<=m['RF_contract']['owner_gate_state_reserved_bits']

@pytest.mark.parametrize('bad',[(0,0,1,1,31),(7,4096,1,1,31),(7,0,0,1,31),(7,0,1,1,32),(7,0,1,0,31),(7,0,2**40,1,31)])
def test_ticket_rejection_preserves_credit(owner,bad):
    with pytest.raises(ValueError):owner.accept(bad,[0],[1])
    assert owner.unrelated_request_ready()

@pytest.mark.parametrize('reads,writes',[([512],[0]),([-1],[0]),([0],[]),([0],[0,1,2]),(list(range(6)),[0])])
def test_home_capacity(owner,reads,writes):
    with pytest.raises(ValueError):owner.accept(T,reads,writes)
    assert owner.owner is None

@pytest.mark.parametrize('bits', [32,64])
def test_select_order_cost_and_atomicity(owner,bits):
    cost=V.command_cost('SELECT',[32,bits,bits],bits)
    reads=list(range(cost['RF_read_vectors']));writes=list(range(510,510+cost['RF_write_vectors']))
    owner.accept(T,reads,writes)
    with pytest.raises(ValueError):owner.accept((7,1,2,1,31),[],[1])
    while owner.phase=='reading':
        assert not owner.unrelated_request_ready();pair=owner.read(T)
        assert len(pair)<=2
        with pytest.raises(ValueError):owner.read(T)
        with pytest.raises(ValueError):owner.complete(T,native_ticks=1)
        owner.return_read(T,stalls=1)
    owner.complete(T,native_ticks=cost['native_only_replacement_ticks'])
    for addr in writes:
        assert owner.write(T)==addr
        owner.ack(T,0,stalls=2)
        with pytest.raises(ValueError):owner.consumer(T)
        with pytest.raises(ValueError):owner.write(T)
        with pytest.raises(ValueError):owner.ack(T,0,stalls=2)
        owner.ack(T,1,stalls=2)
    assert owner.time==cost['components']['RF_read']+cost['components']['RF_write_visible']+cost['components']['native_only']+cost['RF_read_pair_transactions']+2*cost['RF_write_vectors']
    assert sum(t[0]=='read_accept' for t in owner.transactions)==cost['RF_read_pair_transactions']
    assert sum(t[0]=='both_mirrors_ACK' for t in owner.transactions)==cost['RF_write_vectors']
    owner.consumer(T)
    with pytest.raises(ValueError):owner.retire(T,reverse_grant=False)
    assert not owner.unrelated_request_ready()
    owner.retire(T,reverse_grant=True)
    assert owner.unrelated_request_ready()
    assert [e[0] for e in owner.events]==J.build()['RF_contract']['C0_order']
    with pytest.raises(ValueError):owner.accept(T,reads,writes)

@pytest.mark.parametrize('kind',['read','write'])
def test_excess_stall_does_not_drop_lease(owner,kind):
    owner.accept(T,[0],[1]);owner.read(T)
    if kind=='write':owner.return_read(T);owner.complete(T,native_ticks=1);owner.write(T)
    before=(owner.owner,owner.pending,owner.time)
    with pytest.raises(ValueError):
        if kind=='read':owner.return_read(T,stalls=5)
        else:owner.ack(T,0,stalls=5)
    assert before==(owner.owner,owner.pending,owner.time)
    assert not owner.unrelated_request_ready()

def test_stale_response(owner):
    owner.accept(T,[0],[1]);owner.read(T)
    with pytest.raises(ValueError):owner.return_read((8,1736,1,1,31))
    assert owner.pending is not None

def test_iota_without_fake_read(owner):
    owner.accept(T,[],[0,1]);assert owner.phase=='compute'
    owner.complete(T,native_ticks=5)
    for i in range(2):owner.write(T);owner.ack(T,1);owner.ack(T,0)
    owner.consumer(T);owner.retire(T,reverse_grant=True)
    assert owner.time==9
    assert not any(e[0]=='read' for e in owner.events)
