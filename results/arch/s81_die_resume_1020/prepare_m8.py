"""Apply the generator-equivalent M8 settings to an immutable mu6n case copy."""
from pathlib import Path
import hashlib,json,sys
case=Path(sys.argv[1]); helper=Path(sys.argv[2]); source=sys.argv[3]
manifest={'schema':'s81.mu6b_m8.source_overlay.v1','source_commit':source,'base_source':'12c132d60a8f0300056abb216d48ff9588e7f620','base_dieflow':'804d68ef69adab4aca463317d74bbed100da330d','label':'PILOT_WITH_165_STANDINS_NOT_RELEASE_CLOSURE','changes':[]}
for f in ['run.tcl','sta_tt.tcl','sta_ff.tcl','sta_ss.tcl','die_repeaters_step.tcl','fclk_audit.tcl']:
 p=case/f; old=p.read_bytes(); new=old.decode()
 if f=='fclk_audit.tcl': new=helper.read_text()
 elif f=='die_repeaters_step.tcl':
  assert 'rc_layer {M4}' in new
  new=new.replace('rc_layer {M4}','rc_layer {M8}')
 else:
  new=new.replace('set_wire_rc -signal -layer M6','set_wire_rc -signal -layer M8').replace('-signal M2-M7 -clock M5-M9','-signal M2-M8 -clock M5-M9').replace('layer_adjustment M6-M7 0.20','layer_adjustment M6-M8 0.20')
 p.write_text(new)
 manifest['changes'].append({'file':f,'before':hashlib.sha256(old).hexdigest(),'after':hashlib.sha256(new.encode()).hexdigest()})
manifest['latency_delta_cycles']=0
manifest['full_die_check_required']=['global_route','M8 RC/repeater slew','TT/FF/SS die STA','complete forwarded payload audit','regional clock/ring tolerance']
(case/'codex_source_overlay.json').write_text(json.dumps(manifest,indent=2)+'\n')
