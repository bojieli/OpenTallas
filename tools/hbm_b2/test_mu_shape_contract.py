import importlib.util
import math
from pathlib import Path

spec=importlib.util.spec_from_file_location('mu_shape_contract',Path(__file__).with_name('mu_shape_contract.py'))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_legacy_half_sizing_does_not_cover_full_vector():
    r=m.evaluate()
    assert not r['shape_consistent']
    assert r['covered_words']==2560
    assert math.isclose(r['missing_lane_outline_mm2'],2.86654464)

def test_full_inventory_covers_vector_but_bank_calendar_stays_open():
    r=m.evaluate(lanes=32,external_tree_nodes=28,hub_instances=1)
    assert r['shape_consistent']
    assert r['covered_words']==5120
    assert r['max_lanes_per_bank']==2
    assert r['bank_calendar_status']=='NEEDS_NATIVE_MAPPING_AND_SLOT_CHECK'

def test_time_multiplexing_requires_new_storage_and_counters():
    r=m.evaluate(lanes=16,nm=40,external_tree_nodes=28,hub_instances=1)
    assert r['covered_words']==5120
    assert r['x_store_rows']==160
    assert any('NM > 31' in e for e in r['errors'])
    assert any('128-row' in e for e in r['errors'])


def test_native_bank_option_preserves_capacity_without_hidden_read_ports():
    r=m.vm_tradeoffs();a,b,c=r['cases']
    assert a['regular_words']==131072
    assert b['regular_words']==c['regular_words']==524288
    assert b['full_5120_word_fused_read_floor']==dict(pre=160,post=200)
    assert c['full_5120_word_fused_read_floor']==dict(pre=80,post=100)
    assert r['native32_extra_macros_vs_proxy']==16
    assert not b['existing_RTL_shape']
