import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_service_floor import build

def test_source_count_service_floor_not_proxy():
 d=build();assert sum(p['bytes'] for p in d['phases'].values())==3792896
 assert sum(p['warp_shared_issues'] for p in d['phases'].values())==37568
 assert d['capacity_floor_cases'][0]['shared_serial_cycle_floor']==29632
 assert d['capacity_floor_cases'][1]['shared_serial_cycle_floor']==926
 assert d['capacity_floor_cases'][1]['RF_active_write_serial_cycle_floor']==413
 assert d['rate_credit']==0 and d['whole_token_latency'] is None

def test_query_cache_and_exception_shortcut_not_free():
 d=build();assert d['query_full_cache_scope']['plus64raw_keys_bytes']==66048>65536
 assert d['query_full_cache_scope']['cachequeryonce_not_admitted']
 assert d['phases']['exceptional_selection_merge_always']['bytes']==2195456
 assert d['exceptional_only_branch_work']['branch_latency'] is None
 assert d['RF_known_active_read_bits_lower_bound']==37617664
 assert d['RF_known_active_write_bits_lower_bound']==54132736
