"""Freeze new scratch acceptance on both valid and ready, retaining old replies.

Additive successor of the existing manifest emitter; originals remain intact.
The64 ANDs fit its prospective control budget, no FF/port/pipeline changes.
"""
import hashlib,json
from pathlib import Path
from tools.gpu_sys import canonical_qwen_manifest_install as P
OUT=P.ROOT/'rtl/model/qwen_hbm_manifest_factory_20261003_r4'
def generate(out=OUT):
 out=P.generate(out)
 b=json.loads((out/'ports.json').read_text());top=out/(b['top']+'.sv')
 s=top.read_text()
 s=P.once(s,'\nwire [6:0] selected_PC;','\nwire [63:0] raw_scratch_client_ready;\nwire [6:0] selected_PC;')
 s=P.once(s,'.client_ready(scratch_client_ready[i]),','.client_ready(raw_scratch_client_ready[i]),')
 s=P.once(s,'\nendmodule','\nassign scratch_client_ready=raw_scratch_client_ready & source_owner_workspace_new_admit;\nendmodule')
 top.write_text(s)
 b['source_sha256'][str(top.relative_to(P.ROOT))]=hashlib.sha256(s.encode()).hexdigest()
 b['scratch_new_admit_join']=dict(new_valid='scratch_client_valid[i] && source_owner_workspace_new_admit[i]',new_ready='raw_scratch_client_ready & source_owner_workspace_new_admit',held_response='unchanged actual mux saved contender; new_admit does not gate done/rdata/done_ready',added_AND2=64,FF_added=0,ports_added=0,cycles_added=0,cost='within existing model_r3 prospective512NAND2/SM budget; actual mapping/wire/SSFF unknown')
 (out/'ports.json').write_text(json.dumps(b,indent=2)+'\n')
 return out
if __name__=='__main__':print(generate())
