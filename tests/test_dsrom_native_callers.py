import importlib.util,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('native_model',ROOT/'tools/dsrom_shared_native_vm_model.py')
M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
R=ROOT/'rtl/model_ready_ds_shared_native_20261003'
def test_source_selected_service_state_and_no_free_port():
 c=M.model()['caller_integration']
 assert c['native_write_mux']['port_count_added']==0
 assert c['native_write_mux']['state_bits']==6 and c['shared_VX_mux']['state_bits']==6
 assert c['shared_arbiter_fault_bits']==1 and c['format_fault_bits']==1
 assert c['added_FF_floor_um2']==3263*.2916
 assert c['indexer']['state_bits_added']==3028
 assert not c['physical_admission']
def test_new_sources_exactly_pinned_and_historical_scope_retained():
 m=M.model()
 for n in ('me','att','idx_pool','xu'):
  p='rtl/model_ready_ds_shared_native_20261003/ot_hdc_v41x_'+n+'_adapt_native_vm.sv'
  assert m['source_sha256'][p]==hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
 assert not m['admission']['complete_seven_class_parent'] and not m['admission']['protected_parent']
def test_read_lock_reset_debt_and_real_service_join():
 a=(R/'ot_ds_native_engine_arbiter.sv').read_text()
 assert 'else if(!rst_n && outstanding)fault<=1' in a
 assert 'rstate==2 && vm_reply_v && vm_reply_ready' in a
 assert 'wstate!=2' in a and 'vm_reply_owner[59+:32]' in a
 p=(R/'ot_ds_native_seven_caller_service.sv').read_text()
 assert 'ot_ds_native_vm_related_callers' in p and 'ot_ds_native_engine_arbiter' in p
 assert 'element >= 31\'d524288' in p
 assert 'element>>4' in p and 'selector_w_elementaddr[3:0]+l' in p
def test_complete_attention_stored_format_and_finite_index_batch():
 a=(R/'ot_hdc_v41x_att_adapt_native_vm.sv').read_text()
 assert 'D!=512 || TROWS!=640' in a and '!PACKED_KV' in a
 assert 'x_reply_cookie != pending_cookie' in a
 assert 'wc < wend' in a and 'write_debt<=0' in a
 p=(R/'ot_hdc_v41x_idx_pool_adapt_native_vm.sv').read_text()
 assert 'score_fifo[0:63]' in p and 'merge_v && next_batch_room' in p
 assert 'score_count==64 && score_pop==0' in p
 assert 'packet_data[(slot*W+lane)*32+:32]={record[16:1],16\'d0}' in p

def test_actual_core_calls_selected_copies_with_issuer_pc():
 p=(R/'ot_hdc_core_v41x_native_callers.sv').read_text()
 assert 'parameter integer NATIVE_VM=0' in p
 for n in ('me','att','idx_pool','xu'):assert 'ot_hdc_v41x_'+n+'_adapt_native_vm #' in p
 assert 'if(e_go[3])native_issue_pc[1]<=pc' in p
 assert '.x_q(NATIVE_VM ? native_vx_q_data[1*128+:128] : vx_q)' in p
 assert '.write_visible(native_w_visible[3])' in p
 assert not M.model()['admission']['complete_seven_class_parent']
