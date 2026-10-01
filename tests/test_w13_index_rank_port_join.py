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
