from pathlib import Path
import re,json,hashlib
out=Path(__file__).resolve().parent
pp=Path('/srv/opentallas-scratch/claude/codex-storeA-source-lineage-0550/selected_preprocessed.sv').read_text()
ctl=(out.parent/'hbm_ctl_native_intake_0440/closure_ot_hgi_sfu_core_split3__ctl.sv').read_text()
names=['ot_hgi_sfu_vm_static_bridge','ot_hgi_sfu_lg_pair_tap_leaf','ot_hgi_sfu_lg_pair_leaf','ot_hbm_vm_lg_pair_tap','ot_hbm_vm_lg_static_bank','ot_hbm_vm_lg_keep_reg','ot_hdc_delay']
mods=[]; hashes={}
for n in names:
 text=ctl if n=='ot_hgi_sfu_vm_static_bridge' else pp
 m=re.search(r'^module\s+'+n+r'\s*(?:#|\()',text,re.M);assert m,n
 e=text.index('endmodule',m.start())+len('endmodule')
 raw=text[m.start():e];hashes[n]=hashlib.sha256(raw.encode()).hexdigest()
 mods.append(re.sub(r'^`line.*$','',raw,flags=re.M))
(out/'native_modules.sv').write_text('`timescale 1ns/1ps\n'+'\n'.join(mods)+'\n')
(out/'source_hashes.json').write_text(json.dumps(hashes,indent=1)+'\n')
