"""Changed physical receiver anchors and fail-closed census enrollment only."""
import json,hashlib
from pathlib import Path
import pytest
from tools.gpu_sys import canonical_qwen_input_bank_install as I

def test_actual_r4_receiver_links_replace_one_driver_each():
 s=(I.BASE/'ot_gpu_qwen_hbm_integrated_scratch.sv').read_text()
 outputs=['root_inputs_bound_valid','root_inputs_bound_tuple','root_inputs_bound_mask','root_row_barrier_ready','root_input_terminal_ready','root_input_reverse_ready','root_frame_retire_ready','bank_inputs_bound_ready','bank_go_accepted','bank_go_tuple','bank_input_terminal_valid','bank_input_reverse_valid','bank_frame_retire_valid','bank_input_terminal_tuple','bank_input_reverse_tuple','bank_frame_retire_tuple','bank_input_terminal_mask','bank_input_reverse_mask','bank_issuer_held_valid','bank_issuer_held_fault','bank_issuer_held_tuple','bank_issuer_held_owner','bank_frame_retire_owner']
 for p in outputs:
  target=I.LINKS[p]
  assert sum(l.strip().startswith('assign '+target+'[') for l in s.splitlines())==1,target
 assert 'assign scratch_client_ready=raw_scratch_client_ready & source_owner_workspace_new_admit;' in s
 assert '|| (|scratch_fault)' in s
 assert 'assign local_shared_router_drained=kv_shared_drained && (&scratch_drained);' in s
 assert 'assign source_owner_next_source_PC[i*11 +: 11]=issuer_issue_tuple[i*239+164 +: 11];' in s

def test_missing_actual_source_profile_cannot_generate_ready_top(tmp_path):
 p=tmp_path/'profile.json';p.write_text(json.dumps({'source_complete':False,'mutable_state_bits':0}))
 with pytest.raises(ValueError,match='actual complete immutable'):I.generate(p,tmp_path/'never')
 assert not (tmp_path/'never').exists()

def test_terminal_pins_and_defaultoff_no_initializer_or_source_release():
 d=I.ROOT/'rtl/model/qwen_input_bank_barrier_20261003';t=json.loads((d/'directed_r3/terminal.json').read_text())
 assert t['verdict']=='PASS_ATOMIC_BANK_JOIN_FIXTURE'
 for p,h in t['source_sha256'].items():assert hashlib.sha256((I.ROOT/p).read_bytes()).hexdigest()==h
 s=(I.ROOT/I.JOIN).read_text()
 assert 'parameter bit ENABLE=0' in s
 assert 'bank_input_terminal_valid[b]=root_input_terminal_valid[actor] && root_input_terminal_ready[actor]' in s
 assert 'bank_input_reverse_valid[b]=root_input_reverse_valid[actor] && root_input_reverse_ready[actor]' in s
 assert 'bank_frame_retire_valid[b]=root_frame_retire_valid[actor] && root_frame_retire_ready[actor]' in s
 assert 'source_release' not in I.LINKS and 'initial_go_ready' not in I.LINKS
