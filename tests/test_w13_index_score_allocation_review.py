import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_score_allocation_review import build

def test_source_trace_capacity_rejection_scope():
 d=build();assert d['selected_trace_events']==1237
 assert d['conservative_symbol_interval_peak']==34
 assert d['address_loop_reserved_registers']==8 and d['combined_strategy_register_demand']==42>32
 assert '32registers_exceeded' in d['allocation_issues']
 assert not d['physical_register_assignments_admitted'] and not d['physical_admission']

def test_actual_tile_metrics_not_static_proxy_or_old_fit():
 d=build();assert d['actual_source_produced_key_rows']==64 and d['distinct_raw_key_rows']==64 and d['distinct_produced_key_rows']==60
 assert not d['whole64_SSA_expanded'] and not d['old_joint_63488_fit_reusable']
 assert d['executed_whole64_software_metrics']['shared_requested_bytes']==3792896
 assert d['executed_whole64_software_metrics']['shared_warp_issues']==37568
 assert d['checkpoint_reads']==0 and d['physical_provider_timeline'] is None
