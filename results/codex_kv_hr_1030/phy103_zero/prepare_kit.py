#!/usr/bin/env python3
"""Isolated frozen103 PHY M1 zero-credit candidate. No PLACE/route is launched."""
from pathlib import Path
import argparse,shutil,json,re,hashlib,importlib.util
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=argparse.ArgumentParser();a.add_argument('--base',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--source-commit',required=True);a.add_argument('--plan-sha',required=True);ns=a.parse_args();P=Path(__file__).parent;K=ns.out
assert not K.exists(),K
shutil.copytree(ns.base,K,ignore=shutil.ignore_patterns('run','lec','lec_post','signoff','__pycache__','PROVENANCE.json','1_synth_odb.v'))
old='ot_sram_1r1w_512x128_m2_r2c2';new='ot_sram_1r1w_512x128_m1_r2c2'
for f in (K/'rtl').glob('*'):f.unlink()
shutil.copy2(P/'rtl/qkd_hr_phy_adp.v',K/'rtl/qkd_hr_phy_adp.v');shutil.copy2(P/'macro_views'/new/(new+'_bb.v'),K/'rtl'/(new+'_bb.v'))
shutil.rmtree(K/'macros');(K/'macros').mkdir()
for suffix in ['.lef','_tt.lib','_ff.lib']:shutil.copy2(P/'macro_views'/new/(new+suffix),K/'macros'/(new+suffix))
text=(K/'config.mk').read_text().replace(old,new).replace('129_6x86_4','103_68x95_04')
text=re.sub(r'^export CORE_AREA = .*$', 'export CORE_AREA = 4.32 4.32 99.36 90.72',text,flags=re.M)
for key,value in {'TC_LIB_FILES':f'$(TC_NLDM_LIB_FILES) /work/macros/{new}_tt.lib','BC_LIB_FILES':f'$(BC_NLDM_LIB_FILES) /work/macros/{new}_ff.lib','ADDITIONAL_LEFS':f'/work/macros/{new}.lef','ADDITIONAL_LIBS':f'/work/macros/{new}_tt.lib','PRE_GLOBAL_PLACE_TCL':'/work/phy_face_sites.tcl','PRE_DETAIL_PLACE_TCL':'/work/phy_face_release.tcl'}.items():text=re.sub(r'^export '+key+r' = .*$',f'export {key} = {value}',text,flags=re.M)
(K/'config.mk').write_text(text)
# Actual M1 SRAM PG is M4; inherited macro-grid M5/M6 alone leaves both supplies physicallyopen.
shutil.copy2(P/'pdn_m4.tcl',K/'pdn.tcl')
# No pin coordinate/layer/shape change: exact canonical560 records and existing generated IO.
assert json.load(open(K/'pins.json'))==json.load(open(P/'pins.json'))
shutil.copy2(P/'canonical_pins.json',K/'canonical_pins.json')
shutil.copy2(P/'flow_tools/reg_fanout_gate.py',K/'reg_fanout_gate.py')
(K/'macro_place.tcl').write_text(f'''set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set hit {{}}
foreach i [$b getInsts] {{if {{[[$i getMaster] getName] eq "{new}"}} {{lappend hit $i}}}}
if {{[llength $hit]!=1}} {{error "expected exactly one M1 SRAM"}}
set i [lindex $hit 0];$i setOrient R0;$i setLocation [expr {{round(30.24*$u)}}] [expr {{round(12.972*$u)}}];$i setPlacementStatus FIRM
''')
plan_path=P/'native_legal_ff_plan.json'
assert plan_path.exists(), 'TAP-safe native homes required; preserve old planned-only packet as history'
plan=json.load(open(plan_path));sites=plan['cells'];rows=[]
read_sites=[c for c in sites if c['role'].startswith('SRAM')]
assert len(read_sites)==128 and all('rb_cap' in c['cell'] for c in read_sites), 'macro first read capture must be rb_cap, not downstream rr_d'
for cell in sites:rows.append('\t'.join([cell['cell'],cell['master'],str(cell['bbox'][0]),str(cell['bbox'][1]),str(int(cell['role'].startswith('SRAM')))]))
(K/'phy_ff_sites.tsv').write_text('\n'.join(rows)+'\n')
(K/'phy_face_sites.tcl').write_text('''source /work/face_flops.tcl
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set orient {}
foreach row [$b getRows] {dict set orient [lindex [$row getOrigin] 1] [$row getOrient]}
set f [open /work/phy_ff_sites.tsv r];set count 0
while {[gets $f line]>=0} {
 lassign [split $line "\t"] name master x y private
 set i [$b findInst $name]
 if {$i eq "NULL"} {error "first-FF mapping missing $name"}
 if {[[$i getMaster] getName] ne $master} {error "first-FF master changed $name"}
 set xx [expr {round($x*$u)}];set yy [expr {round($y*$u)}]
 if {![dict exists $orient $yy]} {error "first-FF site is not a legal row $name"}
 $i setPlacementStatus PLACED;$i setOrient [dict get $orient $yy];$i setLocation $xx $yy;$i setPlacementStatus FIRM
 incr count
}
close $f;puts "PHY_ZERO_M1_FIRST_FF_SITES $count"
''')
(K/'phy_face_release.tcl').write_text('''source /work/face_flops_release.tcl
set b [ord::get_db_block];set f [open /work/phy_ff_sites.tsv r]
while {[gets $f line]>=0} {
 lassign [split $line "\t"] name master x y private
 if {!$private} continue
 set i [$b findInst $name]
 if {$i ne "NULL" && [$i getPlacementStatus] eq "FIRM"} {$i setPlacementStatus PLACED}
}
close $f
''')
for f in list(K.glob('face_guard*.json'))+list(K.glob('reg_fanout*.json'))+list(K.glob('port_bind*.json')):f.unlink()
core=json.load(open(K/'core.json'));core['candidate_counter_encoding']=json.load(open(P/'zero_credit_recode.json'));(K/'core.json').write_text(json.dumps(core,indent=1)+'\n')
fr=json.load(open(K/'freeze.json'));fr.update(type='qkd_hr_phy_adp__103.68x95.04',outline_um=[103.68,95.04],plan_sha256=ns.plan_sha,pins_file=str(K/'canonical_pins.json'),pins_sha256=sha(K/'canonical_pins.json'),pins_canon_sha256=sha(K/'canonical_pins.json'),core_json_sha256=sha(K/'core.json'),macros=[new],source_commit=ns.source_commit)
fr['candidate_scope']='frozen560pins/103.68x95.04; mux1samecapacity; directcreditprotocol0cycles with counterstateencoding; no adoption'
fr['kit_hash']=hashlib.sha256(((K/'config.mk').read_text()+(K/'rtl/qkd_hr_phy_adp.v').read_text()+sha(K/'macros'/(new+'.lef'))).encode()).hexdigest()[:16]
(K/'freeze.json').write_text(json.dumps(fr,indent=1)+'\n')
(K/'credit_return_capture.json').write_text(json.dumps({'schema':'opentallas.hr.credit_capture.v1','module':'qkd_hr_phy_adp','default':0,'return_latency_edges':0,'credit_capacity_delta':0,'vehicle_parameter':0,'enabled_by':'NONE: zero-cycle counter state encoding; optional +1 pipeline disabled'},indent=1)+'\n')
shutil.copy2(P/'zero_credit_recode.json',K/'zero_credit_recode.json')
spec=importlib.util.spec_from_file_location('kit_lec',K/'lec.py');lec=importlib.util.module_from_spec(spec);spec.loader.exec_module(lec)
lec.write_kit_provenance(K,P,provenance={'commit':ns.source_commit,'dirty':False,'source':'committed CODEX candidate packet'})
print(json.dumps({'prepared':str(K),'kit_hash':fr['kit_hash'],'public_pins':560,'cycles_added':0,'macro':new,'status':'SYNTH/FACE/LEC pending; NO PLACE launched'},indent=1))
