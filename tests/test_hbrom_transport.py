import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import hbrom_transport as T


def node(name, deps=(), kind='vector',layer=0,**kw):
    return dict(id=name,deps=list(deps),kind=kind,layer=layer,duration_ns=100.,resources=[],**kw)


def test_endpoint_packet_reproduces_actual_full_residual_fixture():
    p=T.packet_cost(40976)
    assert p['flits']==641
    assert p['cycles']==909
    assert p['duration_ns']==757.5
    assert T.packet_cost(147456)['duration_ns']>1920


def test_whole_layer_capacity_rounds_groups_not_average():
    p=T.pack_layers([7,7,7],4,2)
    assert p['dies']==6
    assert p['groups']==[[0],[1],[2]]
    with pytest.raises(ValueError):T.pack_layers([9],4,2)


def test_gathers_are_completed_rows_and_no_tp1_wire():
    assert T.gather_cost(20480,1)['duration_ns']==0
    assert T.gather_cost(20480,4)['bytes_per_rank']==15360
    assert T.gather_cost(20480,8)['rounds']==7


def test_join_down_order_and_baseline_immutability():
    nodes=[node('L0.ffn.quant2'),node('L0.ffn.shared_quant'),
           node('L0.ffn.down:component0',['L0.ffn.quant2'],kind='weight'),
           node('L0.ffn.down',['L0.ffn.down:component0'],kind='join'),
           node('L0.ffn.combine_allreduce',['L0.ffn.down'],kind='collective',original={'payload':20480,'op':'all_reduce'})]
    saved=copy.deepcopy(nodes); out=T.reprice_nodes(nodes,2); by={n['id']:n for n in out}
    assert nodes==saved
    assert by['L0.ffn.down:component0']['deps']==['L0.ffn.down_input_gather']
    assert by['L0.ffn.combine_allreduce']['deps']==['L0.ffn.ordered_expert_sum']
    assert by['L0.ffn.ordered_expert_sum']['duration_ns']>0
    assert by['L0.ffn.combine_allreduce']['hbrom_transport']['op']=='output_allgather'
    with pytest.raises(ValueError):T.reprice_nodes(out,4)


def test_hops_follow_actual_layer_groups():
    nodes=[]
    for l in range(4):
        nodes.extend([node(f'L{l}.attn.start',[] if l==0 else [f'L{l-1}.ffn.hc_post'],layer=l),
                      node(f'L{l}.ffn.hc_post',[f'L{l}.attn.start'],layer=l),
                      node(f'L{l}.substage_hop0',[f'L{l}.attn.start'],kind='hop',layer=l,original={'hop_kind':'substage'})])
    out=T.reprice_nodes(nodes,4,2);by={n['id']:n for n in out}
    assert T.transport_summary(out)['neighbor_stage_hops']==1
    assert by['L2.attn.start']['deps']==['L2.hbrom.stage_in']
    assert by['L1.attn.start']['deps']==['L0.ffn.hc_post']
    assert all(n['duration_ns']==0 for n in out if 'substage_hop' in n['id'])


def test_global_width_reprice_no_spurious_tp8_speedup():
    n=node('L0.attn.normalize')
    assert T.reprice_nodes([n],1)[0]['duration_ns']==400
    assert T.reprice_nodes([n],8)[0]['duration_ns']==100
    assert T.reprice_nodes([n],2)[0]['hbrom_transport']['per_rank_work']==16384


def test_selected_rows_transport_is_explicit():
    n=node('L3.attn.rows_allgather',kind='collective',layer=3,original={'payload':215040})
    out=T.reprice_nodes([n],4,1)[0]
    assert out['hbrom_transport']['kv_forwarding']['payload_bytes']==147456
    assert out['hbrom_transport']['kv_forwarding']['hops']==1
    assert 'edge2:transport' in out['resources']


def test_chained_kv_releases_from_payload_producer_and_reserves_ports():
    nodes=[node('L2.attn.rows_allgather',kind='collective',layer=2,original={'payload':215040}),
           node('L2.attn.scores',['L2.attn.rows_allgather'],layer=2),
           node('L2.attn.pv',['L2.attn.scores'],layer=2),
           node('L3.attn.rows_allgather',['L2.attn.rows_allgather'],kind='collective',layer=3,original={'payload':215040}),
           node('L3.attn.scores',['L3.attn.rows_allgather'],layer=3),
           node('L3.attn.pv',['L3.attn.scores'],layer=3)]
    out=T.reprice_nodes(nodes,4,selected_kv_forwarding='chained');by={n['id']:n for n in out}
    assert by['KV2.stage2.visible']['deps']==['L2.attn.rows_allgather']
    handoff=by['KV2.stage3.visible']
    assert handoff['deps']==['KV2.stage2.visible']
    assert 'edge2:transport' in handoff['resources']
    assert 'stage3:selected_kv_slot' in handoff['resources']
    assert handoff['hbrom_transport']['required_extra_sram_bytes_per_rank']==147456
    assert handoff['duration_ns']>T.packet_cost(147456)['duration_ns']
    assert by['L3.attn.rows_allgather']['hbrom_transport']['payload_bytes']==67584
    assert 'KV2.stage3.visible' in by['L3.attn.scores']['deps']
    assert 'KV2.stage3.visible' in by['L3.attn.pv']['deps']


def test_chained_kv_single_slot_overwrite_waits_old_consumers():
    nodes=[]
    for l in (12,13,14,15):
        nodes.extend([node(f'L{l}.attn.rows_allgather',kind='collective',layer=l,original={'payload':215040}),
                      node(f'L{l}.attn.scores',[f'L{l}.attn.rows_allgather'],layer=l),
                      node(f'L{l}.attn.pv',[f'L{l}.attn.scores'],layer=l)])
    nodes.append(node('L8.attn.rows_allgather',kind='collective',layer=8,original={'payload':215040}))
    by={n['id']:n for n in T.reprice_nodes(nodes,4,4,selected_kv_forwarding='chained')}
    assert 'L12.attn.pv' in by['KV14.stage3.visible']['deps']
    assert 'L13.attn.pv' in by['KV14.stage3.visible']['deps']
