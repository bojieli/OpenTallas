import copy,json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030');S=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029');D0=Path('/srv/opentallas-scratch2/claude/codex-ds-native-1029')
sys.path[:0]=[str(R/'code'),str(S/'tools/s81_dv'),str(S/'tools/die_plan')]
from layer_prog.entry_page_protocol import encode_programme
from native_phase import seqhost_phase_contract
import dv_layer_compile as D
read=lambda p:json.loads(p.read_text())
t=read(D0/'timing_current.json');phase=read(D0/'seqhost_current.json');t.update(seqhost_input_clock=seqhost_phase_contract(phase))
pages=[read(p)for p in sorted((R/'load_pages_L14').glob('job*.json'))]
record,jobs,streams=encode_programme(pages,t,stage=0,start_phase=0,source_root=S,manifest='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json',inventory=read(R/'inventory_vn.json'))
out=R/'shared_pages_L14';out.mkdir()
for n,(j,w)in enumerate(zip(jobs,streams)):
 (out/f'job{n:03d}.json').write_text(json.dumps(j,indent=1)+'\n');(out/f'job{n:03d}.host_boot.memh').write_text(D.memh(w,515))
record['selected_reset_relative_KS_pin_phase']=seqhost_phase_contract(t)['accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4'];(R/'shared_L14.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
