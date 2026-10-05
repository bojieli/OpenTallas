import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_parallel_transport_contract as T


def test_PHW10_source_fullbus_not1616_data_only():
    src=(ROOT/'results/uarch/dsrom_native_mode_contract_20261002/inputs/ot_v41_spine_w17w10.sv').read_text()
    assert T.width_expression(src,10)==1632
    assert T.width_expression(src,6)==1628
    assert 549+1067==1616 and 1632-1616==16
    assert T.packet_bits('FULL')==1681 and T.packet_bits('ROOT')==108
    assert T.packet_bits('CFG')==37
    with pytest.raises(ValueError):T.packet_bits('NARROW')


def test_cfg27_safeedge_with_actual_nonblocking_register_pipeline():
    r=T.cfg_edges(4)
    assert r['ROM_read_edges']==list(range(5,30))
    assert [e['edge'] for e in r['element_cfg_capture']]==list(range(6,31))
    assert [e['ROM_word'] for e in r['element_cfg_capture']]==list(range(25))
    assert r['last_cfg_capture_edge']==30 and r['source_safe_GO_edge']==31
    assert not r['actual_hard_ROM_CLKQ_ECC_capture_or_delivery_fence_qualified']


def test_source_expression_mutant_no_unrestricted_eval():
    with pytest.raises(ValueError):T.width_expression('parameter integer BW = unknown + 1')
    with pytest.raises(ValueError):T.width_expression('parameter integer BW = PHW * 100')


def replica_inputs():
    import json
    field=json.loads(T.E.READBACK.read_text())['compiled_field']
    provider=next(T.C.readrows(T.E.OUT/'export_r1/FP4_ECC_provider_directory.jsonl.gz'))
    return field,provider


def test_same_PAR2_local_replica_uses_only_charged_q_padding_no_bitloss():
    f,p=replica_inputs();r=T.local_replica_plan(f,p)
    assert r['extra_complete_pairs_used']==103 and r['extra_weight_macro_instances']==0
    assert r['remaining_shard1_padding_pairs']==281
    assert set(r['mirror_pairs'])<=set(f['padding_site_IDs'])
    assert not set(r['mirror_pairs'])&set(f['BF_DUAL_site_IDs'])
    for bit in [0,255,256,4194303,4194304,p['bits']-1]:
        a=T.local_sidecar_address(r,bit,0);b=T.local_sidecar_address(r,bit,1)
        assert a['shard']==0 and b['shard']==1
        assert [a[k] for k in ('mb','parity','physical_row','data_bit')]==[b[k] for k in ('mb','parity','physical_row','data_bit')]
    assert not r['actual_read_ports_or_SSFF_qualified']


def test_local_copy_cannot_borrow_active_matrix_site_or_truncate_capacity():
    import copy
    f,p=replica_inputs();bad=copy.deepcopy(f);bad['padding_site_IDs'][0]=2048
    with pytest.raises(ValueError):T.local_replica_plan(bad,p)
    bad=copy.deepcopy(f);bad['padding_site_IDs']=[i for i in f['padding_site_IDs'] if i//2048==0]
    bad['weight_active_site_IDs']=sorted(set(range(4096))-set(bad['padding_site_IDs']))
    with pytest.raises(ValueError):T.local_replica_plan(bad,p)
    r=T.local_replica_plan(f,p)
    with pytest.raises(ValueError):T.local_sidecar_address(r,p['bits'],1)
