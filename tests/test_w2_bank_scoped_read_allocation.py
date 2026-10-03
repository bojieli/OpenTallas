import importlib.util
from pathlib import Path
S=importlib.util.spec_from_file_location('alloc',Path(__file__).resolve().parents[1]/'tools/w2_bank_scoped_read_allocation.py');M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_source_exact_parallel_domains_and_no_selfrepair():
 d=M.model()['allocation'];assert d['controllers_per_die']==128 and d['engine_count_per_PC']==8
 for e in range(6):assert d['table_engines'][str(e)]==list(range(16*e,16*e+16))
 for e in (6,7):
  targets=d['utility_targets'][str(e)];assert len(targets)==120 and not set(range(145+3*e,148+3*e))&set(targets)
 assert set(range(96))|set(d['utility_targets']['6'])|set(d['utility_targets']['7'])==set(range(219))
def test_selector_bound_accounts_both_current_read_and_peer_cones():
 d=M.model()['selector_budget'];assert d['candidate_raw_fixed_bitmux_upper']==47232;assert d['candidate_peer_context_bitmux_upper']==2688
 assert d['candidate_NAND2_upper']==149760
 assert d['upper_removed_NAND2']==1984896
 assert 'not a measured gain' in d['scope']
def test_no_fault_or_singleuser_parallelism_shortcut():
 d=M.model();assert d['concurrency']['normal_single_user_added_edges']==0
 assert d['concurrency']['source_repair_recurring_II']==9
 assert not d['new_RTL'] and not d['new_job'] and d['current_mapped_result'] is None
 assert d['rejected_replica_reduction']['absolute_token_penalty'] is None
