import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_rank_port_join import build,work

def test_authoritative_rank_tile_coverage_and_tails():
 d=build();assert len(d['operations'])==8
 assert d['aggregate_keys_across_source_ranks']==6815744
 assert d['aggregate_tiles_across_source_ranks']==106848
 assert d['aggregate_full64tiles']==106080 and d['aggregate_tailtiles']==768
 assert {r['tail_keys'] for o in d['operations'] for r in o['ranks']}=={16,24,40,48}
 assert all(r['physical_die_SM_assignment'] is None for o in d['operations'] for r in o['ranks'])

def test_source_port_contract_and_complete_model_not_admitted():
 d=build();assert work(64)['source_shaped_shared_bytes']==3828224
 assert work(64)['source_shaped_shared_issues']==38092
 assert d['full64_fixture_capacity_floor']['ideal32SM_contract_shared_issue_cycles']==1191
 assert d['model_port_contract']['physically_measured_rates'] is None
 assert d['whole_token_cycles'] is None and d['model_admission']=='FAIL_CLOSED'
 assert not d['query_cache_credit'] and not d['partition_query_replication_padding_refill_cost_included']

def test_full_rank_aggregate_pool_floor_rejects_old_budget():
 d=build();floors=d['per_rank_aggregate_pool_lower_floors']
 assert len(floors)==96
 for r in floors:
  assert r['full64tiles']==1105
  assert r['fulltile_shared_issues']==42091660
  assert r['ideal32SM_aggregate_pool_cycles']==1315365
  assert r['ideal32SM_aggregate_pool_cycles']!=1105*1191
  assert abs(r['candidate_0p9GHz_microseconds']-1461.5166666666667)<1e-9
  assert r['budget_verdict']=='FAIL_CURRENT_LOWERING_BUDGET'
 assert d['whole_token_cycles'] is None and not d['hardware_launch']
