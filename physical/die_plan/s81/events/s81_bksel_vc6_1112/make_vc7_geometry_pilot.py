#!/usr/bin/env python3
"""Private BKSEL vC7 geometry pilot, no RTL/latency/clock-constraint change.
Refuses overwrite. SOURCE and DEST may be set to stage on another admitted host.
"""
import os
from pathlib import Path
import shutil,re,json
base=Path(os.environ.get('SOURCE','/srv/opentallas-scratch2/claude/die-s81-85/bksel_vC6c')); out=Path(os.environ.get('DEST',str(base.with_name('bksel_vC7geo'))))
assert not out.exists(),out
# The legacy runner defaults to async but older kits omitted its helper. Never silently serialize hours of LEC.
helper_arg=os.environ.get('LEC_HELPER')
helper=Path(helper_arg) if helper_arg else next((p/'tools/die_plan/lec_async.sh' for p in Path(__file__).resolve().parents if (p/'tools/die_plan/lec_async.sh').is_file()),Path('__MISSING_CORE_ASYNC_HELPER__'))
if not (base/'lec_async.sh').is_file() and not helper.is_file():
    raise SystemExit('Missing core async helper; set LEC_HELPER to the active core cohort lec_async.sh before staging')
skip={'run','render_place','lec','__pycache__','signoff','views','placed.csv','dump_placed.log'}
shutil.copytree(base,out,ignore=lambda p,ns: [n for n in ns if Path(p)==base and (n in skip or n.startswith('sta_') or n.startswith('run_') and n.endswith('.log') or n.startswith('build_') and n.endswith('.log'))])
p=out/'macro_place.tcl';s=p.read_text();s=s.replace('{414.72 345.6 R0}','{414.72 483.84 R0}').replace('{535.68 345.6 R0}','{535.68 483.84 R0}')
old='{{414.72 475.2 R0} {474.48 475.2 R0} {534.24 475.2 R0} {414.72 529.2 R0} {474.48 529.2 R0}'
new='{{414.72 267.84 R0} {518.4 267.84 R0} {414.72 332.64 R0} {518.4 332.64 R0} {414.72 397.44 R0}'
assert old in s;s=s.replace(old,new).replace('ot_s81ph_hq_pk2 {{142.56 200.88 R0}}','ot_s81ph_hq_pk2 {{142.56 200.904 MX}}')
s='# CODEX vC7 geometry: P MX puts low-valid outputs beside FQ; five FQ banks in former upper payload-RAM bay; two displaced payload RAMs in the old FQ bay. Zero added cycles.\n'+s;p.write_text(s)
if not (out/'lec_async.sh').is_file():shutil.copy2(helper,out/'lec_async.sh')
# No shared inputs or failed result files are modified. New physical form starts at synth.
(out/'geometry_change.json').write_text(json.dumps(dict(base=str(base),form=str(out),changes=['P R0 to MX','FQ 5-bank control-local bay','two payload RAMs moved from upper bay to old FQ bay'],added_cycles=0,status='PRIVATE_PLACE_PILOT_NOT_READY'),indent=1)+'\n')
# Inherited stale verdict/artifacts would confuse the new form: retain them in base, omit from new kit.
for p in out.glob('*.previous.*'):p.unlink()
for nm in ['lec_async.done','lec_async.rc','lec_async.pid','lec_async.ready','lec_async.unit_rc','face_guard.json','face_guard_raw.json','reg_fanout.json','image.txt','prd_result.json']:
 p=out/nm
 if p.exists():p.unlink()
(out/'fifo_control_place.tcl').write_text('# CODEX vC7: finite FIFO pointer/count cluster in the P-east control corridor.\n# No logic, clock or stage changes. The P.pi_vp -> ing_wr/f_pop -> SRAM RA cone stays beside its source.\nuplevel #0 {\nset fc_n 0\nset fc_names {}\nforeach i [[ord::get_db_block] getInsts] {\n set nm [$i getName]\n if {![regexp {^u_q\\.u_s\\.(fcnt|frp|frp_b|fwp|fwp_b)(\\\\?\\[|\\$)} $nm]} continue\n if {![br_is_ff $i]} continue\n set x [expr {round((378.0 + ($fc_n % 4)*2.16) * $br_dbu)}]\n set y [expr {round((354.24 + int($fc_n / 4)*2.16) * $br_dbu)}]\n br_put $i $x $y fifo_control\n lappend fc_names $nm\n incr fc_n\n}\nset fh [open $::env(RESULTS_DIR)/ot_bank_regs.txt a]\nforeach nm $fc_names { puts $fh $nm }\nclose $fh\nputs "CODEX_FIFO_CONTROL: $fc_n state registers in the P-east corridor"\n}\n')
p=out/'pre_gpl_vB.tcl';p.write_text(p.read_text()+'\nsource /work/fifo_control_place.tcl\n')
print(out)
