"""Check capacity exclusions and role replication before candidate selection."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from hbrom_service_area import service_area, build


def test_service_reservation_exceeds_known_primitive_floor():
    x=service_area()
    assert x['total_mm2']>116.969
    assert not x['qualified']
    assert not x['complete_measured_inventory']
    names={r['name'] for r in x['components']}
    assert {'SU_VM','HE_projection','quantizers','SRAM_protection_parity','HBM_PHY'}<=names
    assert all(r['area_mm2']>0 for r in x['components'])
    assert len(names)==len(x['components'])


def test_dedicated_roles_pay_additional_dies_and_traffic():
    x=build(12,2)
    d=x['scenarios']['dedicated_four_rank']
    assert d['role_counts']=={'compute_only':12,'dedicated_service':4,'archive':2}
    assert d['HBM_stacks']==16
    assert sum(d['incremental_remote_traffic_B_per_token'].values())==7864320
    assert d['minimum_additional_phase_crossings']==80
    assert not any(r['name']=='HBM_PHY' for r in x['roles']['compute_only']['components'])


def test_replication_and_persistent_capacity_scale():
    a=service_area(index_keys_per_cycle=32,persistent_layers=1)
    b=service_area(index_keys_per_cycle=64,persistent_layers=40)
    aa={r['name']:r for r in a['components']};bb={r['name']:r for r in b['components']}
    assert bb['index_scorer']['area_mm2']==2*aa['index_scorer']['area_mm2']
    assert bb['persistent_windows']['area_mm2']>aa['persistent_windows']['area_mm2']
    assert aa['HBM_PHY']['replicas']==bb['HBM_PHY']['replicas']==4


@pytest.mark.parametrize('kwargs',[{'role':'bad'},{'index_keys_per_cycle':3},{'quantizers':0},{'persistent_layers':True}])
def test_invalid_shapes(kwargs):
    with pytest.raises(ValueError):service_area(**kwargs)


def test_source_roles_do_not_duplicate_index_and_hbm():
    layer=service_area('layer');owner=service_area('source_owner');last=service_area('source_owner_candidates')
    names=lambda x:{r['name'] for r in x['components']}
    assert 'HBM_PHY' not in names(layer)
    assert 'index_scorer' not in names(layer)
    assert 'index_candidate_keys' not in names(owner)
    assert 'index_candidate_keys' in names(last)
    assert all('selected_forward_slot' in names(x) for x in (layer,owner,last))
    assert layer['assumptions']['persistent_layers']==1
    assert layer['total_mm2']<owner['total_mm2']<last['total_mm2']
    head=service_area('head')
    assert {'SU_VM','HE_projection','head_select'}<=names(head)
    assert not {'HBM_PHY','attention_compute','persistent_windows','index_scorer'}&names(head)
