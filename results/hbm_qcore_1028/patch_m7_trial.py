"""Prepare one approved own-copy M7/PG-pin trial; no RTL/cell/clock edits."""
import json,re,hashlib
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-qcore-m7-1029');k=r/'kit'
rows=json.loads((r/'pin_delta.json').read_text())['pins'];by={x['name']:x for x in rows}
ip=k/'core_infra_plan.json';old_hash=hashlib.sha256(ip.read_bytes()).hexdigest()
def fix(o):
 if isinstance(o,list):return[fix(x)for x in o]
 if not isinstance(o,dict):return o
 z={a:fix(b)for a,b in o.items()};n=z.get('name',z.get('port'))
 if n in by:
  nx=by[n]['new_x']
  if 'xy_um'in z:z['xy_um'][0]=nx
  if 'x'in z:z['x']=nx
 return z
for p in k.glob('*.json'):
 d=json.loads(p.read_text());nd=fix(d)
 if nd!=d:p.write_text(json.dumps(nd,indent=1)+'\n')
new_hash=hashlib.sha256(ip.read_bytes()).hexdigest()
for p in k.glob('*.json'):
 s=p.read_text()
 if old_hash in s:p.write_text(s.replace(old_hash,new_hash))
p=k/'master_core_infra.tcl';s=p.read_text()
for n,z in by.items():
 s,num=re.subn(r'(ot_ci_port \{'+re.escape(n)+r'\} \S+ )\S+',lambda m:m[1]+str(z['new_x']),s)
 assert num==1,(n,num)
p.write_text(s)
p=k/'config.mk';s=p.read_text()
assert s.count('export MAX_ROUTING_LAYER = M5')==1 or s.count('export MAX_ROUTING_LAYER = M7')==1
p.write_text(s.replace('export MAX_ROUTING_LAYER = M5','export MAX_ROUTING_LAYER = M7'))
base='/work/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base'
t=[f'read_db {base}/3_place.odb','set b [ord::get_db_block]','set np [llength [$b getBTerms]]',
 'set ni [llength [$b getInsts]]','set clk [$b findBTerm clk_ctl]','set clock_boxes {}',
 'foreach bp [$clk getBPins] {foreach bx [$bp getBoxes] {lappend clock_boxes [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]}}',
 'set m5 [[ord::get_db_tech] findLayer M5]','set tx [[$b findTrackGrid $m5] getGridX]']
for z in rows:
 n=z['name'];old=[round(x*1000)for x in z['old_box_um']];new=[round(x*1000)for x in z['new_box_um']]
 t += [f'set bt [$b findBTerm {{{n}}}]',f'if {{$bt eq "NULL"}} {{error "missing {n}"}}',
  'set bp [lindex [$bt getBPins] 0]','set bx [lindex [$bp getBoxes] 0]',
  'if {[list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]] ne {%s}} {error "old pin mismatch %s"}' % (' '.join(map(str,old)),n),
  f'if {{[lsearch -exact $tx {round(z["new_x"]*1000)}]<0}} {{error "off-track {n}"}}',
  'odb::dbBox_destroy $bx',f'odb::dbBox_create $bp $m5 {" ".join(map(str,new))}',
  f'puts "NEWPIN {n} {z["new_x"]} {(z["new_box_um"][1]+z["new_box_um"][3])/2}"']
t += ['set after_clock {}','foreach bp [$clk getBPins] {foreach bx [$bp getBoxes] {lappend after_clock [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]}}',
 'if {$clock_boxes ne $after_clock || $np!=[llength [$b getBTerms]] || $ni!=[llength [$b getInsts]]} {error "clock/cell/interface count changed"}',
 f'write_db {base}/3_place_pglegal.odb','puts "PG_PIN_PATCH_PASS cells_and_clock_unchanged 12_pins_on_tracks"']
(r/'pin_patch.tcl').write_text('\n'.join(t)+'\n')
(r/'trial_manifest.json').write_text(json.dumps({'scope':'ROOT-approved G2 only; no DRT/release','RTL':'unchanged original k11','macro_placement':'unchanged original k11','clock_cells_and_core_pin':'unchanged','data_pins':'unchanged','infra_pin_delta':rows,'max_routing_layer':'M7','TT_FF_vclk_ps':[250,202.5],'clock_ps':833,'setup_hold_uncertainty_ps':[60,25],'die_extra_M6_M7_OBS_mm2_per_layer':4*224.64*207.36/1e6,'die_capacity_gate':'Requires composed die GRT/FT proof before adoption'},indent=2)+'\n')
