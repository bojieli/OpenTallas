"""Changed combined source selection and receiver connections, no peer rerun."""
import hashlib,json
from pathlib import Path
from tools.gpu_sys import canonical_qwen_banked_atomic_install as I
OUT=I.ROOT/'rtl/model/qwen_hbm_banked_atomic_factory_20261003_r5'
def test_combined_actual_banked_source_and_all_mask_directions():
 b=json.loads((OUT/'ports.json').read_text());s=(OUT/(b['top']+'.sv')).read_text();deps=(OUT/'sources.f').read_text().splitlines()
 assert I.OLD not in deps and deps.count(I.OWNER)==1 and deps.count(I.JOIN)==1
 assert b['manifest_contract']['owner_module']=='ot_gpu_qwen_banked_manifest_range_owner'
 assert 'ot_gpu_qwen_manifest_range_owner #' not in s
 assert 'ot_gpu_qwen_banked_manifest_range_owner #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER),.SM_INDEX(i))' in s
 for n in ['required_bank_mask64','required_input_bank_mask64','required_output_bank_mask64']:
  p=b['pins']['source_owner_'+n]
  assert (p['direction'],p['bits'],p['count'],p['leaf_bits'],p['block'],p['leaf'])==('output',4096,64,64,'source_owner',n)
  assert '.'+n+'(source_owner_'+n+'[i*64+:64])' in s
 assert '.bind_tuple(source_owner_issued_input_live[i] ? source_owner_inputs_bound_tuple[i*239 +: 239] : source_owner_bind_tuple[i*239 +: 239])' in s
 assert '.root_tuple(source_profile_root_tuple)' in s
 assert 'issuer_busy[p] ? issuer_publish_tuple[p*239+:239] : issuer_issue_tuple[p*239+:239]' in s
 assert b['full_build_ready'] is False and b['token_qualified'] is False

def test_actual_join_replaces_local_drivers_and_keeps_safety_and_clock():
 b=json.loads((OUT/'ports.json').read_text());s=(OUT/(b['top']+'.sv')).read_text()
 for p in I.OUTPUTS:
  n=I.LINKS[p]
  assert not any(l.strip().startswith('assign '+n+'[') for l in s.splitlines()),n
  assert '.'+p+'('+n+')' in s
 assert '.producer_binding_ready(actual_allbank_visible_ready)' in s
 assert '.required_output_rows(actual_whole_output_presence)' in s
 assert 'assign scratch_client_ready=raw_scratch_client_ready & source_owner_workspace_new_admit;' in s
 assert '|| (|scratch_fault)' in s
 assert 'assign local_shared_router_drained=kv_shared_drained && (&scratch_drained);' in s
 assert '.clk(stream_clk)' in s
 assert s.count('ot_gpu_sm_q #')==1 # actual generate64, not duplicate emitters
 assert b['inventory']['native_TC_count']==64
 cpp=(OUT/'pin_driver.cpp').read_text()
 for n in ['required_bank_mask64','required_input_bank_mask64','required_output_bank_mask64']:
  assert 'if(name=="source_owner_'+n+'")' in cpp
  assert 'if(name=="source_owner_'+n+'"){auto v=' not in cpp

def test_new_join_terminal_and_pins():
 d=I.ROOT/'rtl/model/qwen_banked_atomic_receiver_20261003/directed_r1'
 t=json.loads((d/'terminal.json').read_text());assert t['verdict']=='PASS_BANKED_OUTPUT_JOIN_FIXTURE'
 assert t['source_sha256']==t['post_sha256']
 for p,h in t['source_sha256'].items():assert hashlib.sha256((I.ROOT/p).read_bytes()).hexdigest()==h
 b=json.loads((OUT/'ports.json').read_text())
 for p in [I.OWNER,I.JOIN,str((OUT/(b['top']+'.sv')).relative_to(I.ROOT))]:
  assert hashlib.sha256((I.ROOT/p).read_bytes()).hexdigest()==b['source_sha256'][p]
 assert b['atomic_bank_join']['original_profile_contract_sha256']==I.digest(I.ROOT/'results/uarch/canonical_qwen_immutable_bank_profile_20261003/contract.json')
