from tools.w17_crom_warm_admission import build
from decimal import Decimal

def test_priced_product_and_topology_closed_beforeRTL():
    r=build()
    assert Decimal(r['extra_product_alone_slot_deficit_mm2'])>0
    assert len(r['affected_reference_owners'])==8
    assert r['warm']['actual_RTLcache_provider'] is None and not r['warm']['live_L0_L20_hit_credit']
    assert r['cold']['actual_TTFT'] is None
    assert r['actual_whole_margin_W'] is None and not r['hardware_admission']
