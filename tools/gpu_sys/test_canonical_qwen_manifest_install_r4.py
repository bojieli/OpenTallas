"""Changed installed admission handshake only; no duplicate RTL build/gate."""
import hashlib,json
from tools.gpu_sys import canonical_qwen_manifest_install_r4 as I

def test_client_acceptance_both_directions_freeze_and_old_reply_survives():
 b=json.loads((I.OUT/'ports.json').read_text());s=(I.OUT/(b['top']+'.sv')).read_text()
 assert 'wire [63:0] raw_scratch_client_ready;' in s
 assert '.client_valid(scratch_client_valid[i] && source_owner_workspace_new_admit[i])' in s
 assert '.client_ready(raw_scratch_client_ready[i])' in s
 assert 'assign scratch_client_ready=raw_scratch_client_ready & source_owner_workspace_new_admit;' in s
 assert '.client_done(scratch_client_done[i])' in s
 assert '.client_done_ready(scratch_client_done_ready[i])' in s
 assert '.client_rdata(scratch_client_rdata[i*512 +: 512])' in s
 assert b['scratch_new_admit_join']['FF_added']==0
 assert not b['full_build_ready']
 p=str((I.OUT/(b['top']+'.sv')).relative_to(I.P.ROOT))
 assert hashlib.sha256(s.encode()).hexdigest()==b['source_sha256'][p]
 for n in ['owner','tuple','valid','exclusive','base','length']:
  assert b['pins']['scratch_workspace_'+n]['direction']=='output'
