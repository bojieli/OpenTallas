import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_mtp_accept_rtl_preparation as P

def test_fullwidth_mutable_state_count():
 m=P.model();assert m['source_assignments']['physical_state_budget_bits']==2016
 assert m['source_assignments']['raw_leaf_and_caller_bits']==716
 assert m['NSLOT']==8 and m['NW']==21 and not m['default_enable']

def test_reset_load_fix_not_extra_stage():
 m=P.model();r=m['reset_reconciliation'];assert r['reset_levels']==[288,36,5,1]
 assert r['clock_levels']==[252,32,4,1]and r['added_BUFF4_minimum']==41
 assert r['old8pin_fF']>r['selected_limit_fF']and r['new7pin_fF']<=r['selected_limit_fF']
 assert r['new_clock_reset_buffers']==619 and m['timing']['extra_codec_stages']==0
 assert m['timing']['accept_to_guarded_done_edges']==3

def test_internal_caller_fault_cut_explicit():
 m=P.model();assert m['ports']['leaf_with_caller_fault_cut']==637
 assert m['ports']['producer_named_cuts']==[52,52]
 assert m['ports']['actual_legal_channel_capacity']is None

def test_no_build_home_or_rate_inference():
 m=P.model();assert not m['admission']['physical_or_P_and_R']
 assert m['admission']['Maxwell_selected_S58_PAR2_stage_rank_shard_map']is None
 assert m['component_gate']['AR_MTP_or_HBM_rate']is None
 assert not m['reset_contract']['externally_false_cold_fence_detected_by_kernel']

def test_stored_preparation_exact():assert json.loads((P.OUT/'preparation.json').read_text())==P.model()
