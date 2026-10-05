"""New receiver installation checks; no whole-top lint or repeated peer gate."""
import hashlib,json,re
from pathlib import Path
from tools.gpu_sys import canonical_qwen_manifest_install as I
D=I.ROOT/'rtl/model/qwen_hbm_manifest_factory_20261003_r3'
S=D/'ot_gpu_qwen_hbm_integrated_scratch.sv'

def test_model_predecessors_and_generated_pin_selection():
 b=json.loads((D/'ports.json').read_text());m=json.loads((I.ROOT/I.MODEL).read_text())
 for p,h in m['source_pins'].items():assert hashlib.sha256((I.ROOT/p).read_bytes()).hexdigest()==h
 for p in [I.OWNER,I.ISSUER,str(S.relative_to(I.ROOT))]:
  assert hashlib.sha256((I.ROOT/p).read_bytes()).hexdigest()==b['source_sha256'][p]
 deps=(D/'sources.f').read_text().splitlines()
 assert deps.count(I.OWNER)==deps.count(I.ISSUER)==1
 assert I.OLDOWNER not in deps and I.OLDISSUER not in deps
 assert b['inventory']['native_TC_count']==64 and b['inventory']['source_owner_count']==64
 assert not b['full_build_ready'] and not b['physical_qualified'] and not b['token_qualified']

def test_one_controller_bank_genuine_engine_and_issuer_root():
 s=S.read_text()
 assert s.count('ot_gpu_qwen_manifest_range_owner #')==1
 assert s.count('ot_gpu_qwen_full_issuer_r3 #')==1
 assert s.count('ot_gpu_sm_q #')==1
 assert s.count('ot_gpu_qwen_scratch_client_mux #')==1
 assert 'parameter bit ENABLE_MANIFEST=0' in s
 assert '.clk(stream_clk)' in s and 'manifest_enabled=ENABLE && ENABLE_MANIFEST' in s
 assert '.required_output_rows(source_owner_required_output_rows)' in s
 assert 'source_owner_go_accepted[i]=(issuer_backend_go_valid[i] && issuer_backend_go_ready[i]) || (issuer_initial_go_valid[i] && issuer_initial_go_ready[i])' in s

def test_workspace_is_physical_root_output_and_child_debt_not_host_positive():
 s=S.read_text();b=json.loads((D/'ports.json').read_text());cpp=(D/'pin_driver.cpp').read_text()
 for n,src in [('valid','source_owner_workspace_held_valid'),('exclusive','source_owner_workspace_held_valid'),('owner','source_owner_workspace_held_owner55'),('tuple','source_owner_workspace_held_tuple')]:
  target='scratch_workspace_'+n
  assert b['pins'][target]['direction']=='output'
  assert 'assign '+target+'='+src+';' in s
  assert f'if(name=="{target}"){{auto v=' not in cpp
 assert 'source_owner_issuer_held_valid[i]=issuer_busy[i]' in s
 assert 'source_owner_issuer_held_fault[i]=issuer_fault[i]' in s
 assert 'source_owner_issuer_held_tuple[i*239 +: 239]=issuer_publish_tuple[i*239 +: 239]' in s
 assert 'source_owner_workspace_children_drained[i]=scratch_drained[i] && kv_shared_drained' in s
 assert 'assign local_shared_router_drained=kv_shared_drained && (&scratch_drained)' in s
 assert '|| (|source_owner_fault) || (|scratch_fault)' in s
 assert '.client_valid(scratch_client_valid[i] && source_owner_workspace_new_admit[i])' in s

def test_initial_channel_and_no_source_bank_relabel():
 s=(I.ROOT/I.ISSUER).read_text()
 assert 'initial_kind ? initial_go_ready : backend_go_ready' in s
 assert re.search(r'assign backend_go_valid=.*native_kind;',s)
 assert re.search(r'assign initial_go_valid=.*initial_kind;',s)
 assert "issue_tuple[174:164]==11'd2047" in s
 assert "issue_tuple[29:19]==11'd2047" in s
 assert 'required_output_rows==0' in s and 'required_output_rows==1 && inputs_bound_mask==0' in s
 assert '.BITS(342)' in s # unchanged coded held root, no new owner/tuple FF copy
 owner=(I.ROOT/I.OWNER).read_text()
 assert 'rt[174:164]==11\'d2047' in owner # immutable INITIAL fact lives in allocator
 assert 'source_input_count' in owner and 'source_output_count' in owner
 assert 'source_native_retire_valid&&source_native_retire_ready' in owner
 b=json.loads((D/'ports.json').read_text())
 assert b['manifest_contract']['provider_bank']=='physicalRF rank/SM kept distinct from execution tuple rank/SM'
