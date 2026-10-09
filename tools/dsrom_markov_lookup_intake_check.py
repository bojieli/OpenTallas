#!/usr/bin/env python3
"""I16 routine receipt binding and routed electrical/anchor acceptance checks."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/w18'))
from corner_sta import script,extra_vts
RTL='rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_localcapture.sv'
SHA='086a450a07eaad25b20477b43ab8fee3c1b983e0c6eca80024b8e0d3ed55560d'
MACRO='physical/asap7_memory_macros/ot_rom_4096x274_m8'
IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
EVIDENCE=ROOT/'results/uarch/dsrom_markov_embed_localcapture_md6_20261009'
def bind():
 assert hashlib.sha256((ROOT/RTL).read_bytes()).hexdigest()==SHA
 gate=json.loads((EVIDENCE/'gate_r1/verdict.json').read_text())
 assert gate['passed'] and gate['checked_beats']==160
 assert gate['source_sha256']['ot_dsrom_markov_embed_localcapture.sv']==SHA
 assert any(r['mutant'] and r['passed'] and r['exit']!=0 for r in gate['results'])
 anchor=json.loads((EVIDENCE/'intake_offline_r3/capture_anchor_audit.json').read_text())
 assert anchor['passed'] and anchor['capture_count']==512 and anchor['RTL_sha256']==SHA
 lint=json.loads((EVIDENCE/'intake_offline_r3/offline_fp_lint.json').read_text())
 assert lint['passed'] if 'passed' in lint else lint['verdict']=='PASS'
 pg=json.loads((EVIDENCE/'pg_fix_c2/verdict.json').read_text())
 assert pg['passed'] and pg['captures']==512 and pg['actual_row_orientation_mismatch']==0
 assert pg['max_actual_q_to_D_manhattan_um']<=20 and pg['VDD_connected'] and pg['VSS_connected']
 assert hashlib.sha256((ROOT/'physical/dsrom_markov_lookup_localcapture/capture_anchor.tcl').read_bytes()).hexdigest()==pg['capture_anchor_sha256']
 return dict(passed=True,RTL_sha256=SHA,checked_beats=160,genuine_mutant_rejected=True,mapped_prerequisite=anchor['anchored_ODB_sha256'])
AUDIT=r'''
foreach ot_port [all_outputs] {puts "OT_I16_OUTPUT [get_full_name $ot_port]"}
write_sdc /receipt/effective.sdc
puts OT_I16_ELECTRICAL_BEGIN
report_check_types -max_slew -max_cap -max_fanout -violators
puts OT_I16_ELECTRICAL_END
set ot_block [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_captures 0;set ot_max_distance 0.0
set ot_row_mismatch 0
foreach ot_macro [$ot_block getInsts] {
 if {[[$ot_macro getMaster] getName] ne "ot_rom_4096x274_m8"} {continue}
 foreach ot_q [$ot_macro getITerms] {
  set ot_pn [[$ot_q getMTerm] getName]
  if {![regexp {^rd_out\[([0-9]+)\]$} $ot_pn -> ot_bit] || $ot_bit>=256} {continue}
  set ot_inputs {}
  foreach ot_t [[$ot_q getNet] getITerms] {
   if {$ot_t ne $ot_q && [$ot_t getIoType] eq "INPUT"} {lappend ot_inputs $ot_t}
  }
  if {[llength $ot_inputs]!=1} {error "payload output requires one direct capture sink"}
  set ot_d [lindex $ot_inputs 0];set ot_ff [$ot_d getInst]
  if {[[$ot_d getMTerm] getName] ne "D" || ![string match *DFF* [[$ot_ff getMaster] getName]]} {error "logic before macro capture"}
  set ot_fb [$ot_ff getBBox];set ot_rows {}
  foreach ot_row [$ot_block getRows] {
   set ot_rb [$ot_row getBBox]
   if {[$ot_fb yMin]==[$ot_rb yMin] && [$ot_fb xMin]>=[$ot_rb xMin] && [$ot_fb xMax]<=[$ot_rb xMax]} {lappend ot_rows $ot_row}
  }
  if {[llength $ot_rows]!=1 || [$ot_ff getOrient] ne [[lindex $ot_rows 0] getOrient]} {incr ot_row_mismatch}
  set ot_qxy [$ot_q getAvgXY];set ot_dxy [$ot_d getAvgXY]
  if {![lindex $ot_qxy 0] || ![lindex $ot_dxy 0]} {error "unplaced capture pin"}
  set ot_distance [expr {(abs([lindex $ot_qxy 1]-[lindex $ot_dxy 1])+abs([lindex $ot_qxy 2]-[lindex $ot_dxy 2]))/double($ot_dbu)}]
  set ot_max_distance [expr {max($ot_max_distance,$ot_distance)}]
  incr ot_captures
 }
}
set ot_leaves 0;set ot_max_leaf 0
foreach ot_net [$ot_block getNets] {
 set ot_clockpins 0;set ot_inputs 0
 foreach ot_t [$ot_net getITerms] {
  if {[$ot_t getIoType] ne "INPUT"} {continue}
  incr ot_inputs
  if {[[$ot_t getMTerm] getName] in {CLK CK clk}} {incr ot_clockpins}
 }
 if {$ot_clockpins>0} {incr ot_leaves;set ot_max_leaf [expr {max($ot_max_leaf,$ot_inputs)}]}
}
puts "OT_I16_CAPTURES $ot_captures"
puts "OT_I16_CAPTURE_DISTANCE $ot_max_distance"
puts "OT_I16_ROW_MISMATCH $ot_row_mismatch"
puts "OT_I16_CLOCK_LEAVES $ot_leaves"
puts "OT_I16_CLOCK_LEAF_MAX $ot_max_leaf"
check_power_grid -net VDD
puts OT_I16_PG_VDD_PASS
check_power_grid -net VSS
puts OT_I16_PG_VSS_PASS
exit
'''
def routed(orfs,out):
 bound=bind();out.mkdir(parents=True,exist_ok=True)
 bases=list(orfs.glob('results/asap7/*/base'))
 assert len(bases)==1
 base=bases[0];rel='/work/'+str(base.relative_to(orfs))
 text=script('tt',rel,[MACRO],['physical/dsrom_markov_lookup_localcapture/gen/signoff_pair.sdc'],vts=extra_vts(base/'6_final.odb'))
 text=text.rsplit('exit',1)[0]+AUDIT
 (out/'audit.tcl').write_text(text)
 cmd=['docker','run','--rm','-v',str(ROOT)+':/src:ro','-v',str(orfs)+':/work:ro','-v',str(out)+':/receipt',IMAGE,'bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /receipt/audit.tcl']
 run=subprocess.run(cmd,capture_output=True,text=True);log=run.stdout+run.stderr;(out/'audit.log').write_text(log)
 def number(name):
  m=re.search(r'^'+name+r'\s+([\d.]+)',log,re.M);return float(m.group(1)) if m else None
 section=log.split('OT_I16_ELECTRICAL_BEGIN')[-1].split('OT_I16_ELECTRICAL_END')[0]
 violations=section.count('(VIOLATED)')
 caps=number('OT_I16_CAPTURES');dist=number('OT_I16_CAPTURE_DISTANCE');leaves=number('OT_I16_CLOCK_LEAVES');fan=number('OT_I16_CLOCK_LEAF_MAX')
 effective=(out/'effective.sdc').read_text() if (out/'effective.sdc').exists() else ''
 outputs=set(re.findall(r'^OT_I16_OUTPUT (.+)$',log,re.M))
 portloads={p:float(v) for v,p in re.findall(r'^set_load -pin_load ([0-9.]+) \[get_ports \{(.+)\}\]$',effective,re.M)}
 explicit_load=len(outputs)==258 and set(portloads)==outputs and all(v==3.898 for v in portloads.values())
 row_mismatch=number('OT_I16_ROW_MISMATCH');pg=all(marker in log for marker in ('OT_I16_PG_VDD_PASS','OT_I16_PG_VSS_PASS'))
 passed=run.returncode==0 and explicit_load and 'OT_I16_ELECTRICAL_END' in log and violations==0 and caps==512 and dist is not None and dist<=20 and row_mismatch==0 and pg and leaves is not None and leaves>0 and fan is not None and fan<=16
 rec=dict(passed=passed,source_binding=bound,returncode=run.returncode,TC_electrical_violations=violations,captures=caps,max_actual_q_to_D_manhattan_um=dist,clock_leaves=leaves,max_clock_leaf_inputs=fan,scope='actual final TT electrical/directcapture/CTSleaf acceptance; setup/hold/DRC independently required')
 rec.update(actual_row_orientation_mismatch=row_mismatch,VDD_VSS_power_grid_connected=pg)
 rec.update(all_258_outputs_have_explicit_unchanged_load_3_898=explicit_load)
 (out/'verdict.json').write_text(json.dumps(rec,indent=2));print(json.dumps(rec));return passed
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--orfs',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
 if a.orfs:raise SystemExit(0 if routed(a.orfs.resolve(),a.out.resolve()) else 1)
 print(json.dumps(bind()))
