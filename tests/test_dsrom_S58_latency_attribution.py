import json
import math
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_S58_latency_attribution as L
@pytest.fixture(scope='module')
def price():return L.build()
def test_exact_replay(price):
    assert price==json.loads((ROOT/'results/uarch/dsrom_current4096_field_receipts_20261002/latency-attribution-r2.json').read_text())
    assert [r['stages'] for r in price['rows']]==[41,58]
def test_longest_path_attribution_not_all_node_work(price):
    for r in price['rows']:
        assert math.isclose(sum(e['exposed_us'] for e in r['critical_path']),r['raw_unrounded_token_us'],abs_tol=1e-7)
    assert math.isclose(sum(price['critical_path_category_deltas_us'].values()),price['unrounded_DAG_delta_us'],abs_tol=1e-7)
    assert math.isclose(price['published_total_delta_us'],29.102533290623)
    assert math.isclose(price['published_nonhop_remainder_us'],22.864533290623)
def test_discrete_BF_reuse_is_priced_at_real_operator_nodes(price):
    wo=[r for r in price['changed_field_events'] if r['operator_key']=='wo_a']
    assert len(wo)==40
    assert all(r['old_t_read']==256 and r['new_t_read']==512 for r in wo)
    assert math.isclose(price['critical_path_field_operator_deltas_us']['wo_a'],17.066666666666684)
    assert math.isclose(price['critical_path_group_deltas_us']['field_bf16'],20.533333333333402)
def test_unchanged_head_die_count_not_free_role_inventory(price):
    h=price['head_scope_risk']
    assert h['retained_head_dies']==8 and h['global_BF_stripe_setting_applies_to_head']
    assert math.isclose(h['lm_head_exposed_delta_us'],3.7333333333333343)
    assert not h['actual_head_residence_under_S58_source_bound']
def test_no_new_selection_or_qualification(price):
    assert price['candidate_id']=='DS4096-TP4-S58-PAIR1'
    assert price['capacity_verdict']=='FAIL_S58_CORRECTED_SERVICE_CAPACITY_SCREEN'
    assert not price['count_selected'] and price['new_counts_swept']==0
    assert not price['RTL_PnR'] and not price['rate_claim']
