#!/usr/bin/env python3
"""Immutable baseline W2 Option B re-STA; run only through fleet admission."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
run=a.run.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
odb=next(run.rglob('results/asap7/*/base/6_final.odb'));spef=odb.with_suffix('.spef');old=next(run.rglob('work/orfs/signoff.sdc'))
oldtext=old.read_text();assert 'set_clock_uncertainty -hold 50 ' in oldtext
sdc=out/'probe.sdc';sdc.write_text(oldtext.replace('set_clock_uncertainty -hold 50 ','set_clock_uncertainty -hold 25 '))
# Preserve all boundary windows and every check type for the first comparison.
tcl=r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(LIBC)_*.lib*]] {read_liberty $f}
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
puts LATBEGIN
report_clock_latency -clock clk_sm -digits 2
puts LATEND
foreach {tag from to} {reg2reg all_registers all_registers in2reg all_inputs all_registers reg2out all_registers all_outputs} {
 foreach d {max min} {
  set paths [find_timing_paths -path_delay $d -from [$from] -to [$to] -group_path_count 1]
  if {[llength $paths]} {puts "SLACK $tag $d [format %.2f [get_property [lindex $paths 0] slack]]"} else {puts "SLACK $tag $d none"}
 }
}
puts "WORST max [format %.2f [sta::worst_slack -max]]"
puts "WORST min [format %.2f [sta::worst_slack -min]]"
report_checks -path_delay max -group_path_count 8 -format full_clock_expanded -digits 2
report_checks -path_delay min -group_path_count 8 -format full_clock_expanded -digits 2
# Include async reset recovery/removal alongside ordinary data paths; never false-path resets.
report_check_types -recovery -removal -violators -digits 2
report_checks -from [get_ports por_n] -path_delay max -group_path_count 4 -format full_clock_expanded -digits 2
report_checks -from [get_ports por_n] -path_delay min -group_path_count 4 -format full_clock_expanded -digits 2
'''
(out/'sta.tcl').write_text(tcl)
def sta(corner,filename,sdcp):
 cmd=['docker','run','--rm','-v',f'{run}:/baseline:ro','-v',f'{out}:/evidence','-e',f'LIBC={corner}','-e',f'ODB=/baseline/{odb.relative_to(run)}','-e',f'SPEF=/baseline/{spef.relative_to(run)}','-e',f'SDC=/evidence/{sdcp.name}','openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /evidence/sta.tcl']
 p=subprocess.run(cmd,capture_output=True,text=True);log=p.stdout+p.stderr;(out/filename).write_text(log)
 if p.returncode or re.search(r'(?m)^\[ERROR|^Error:',log):raise RuntimeError(f'{corner} STA rc={p.returncode}: {log[-3000:]}')
 values={m[1]:float(m[2]) for m in re.finditer(r'^WORST (max|min) (\S+)',log,re.M)}
 lat=log.split('LATBEGIN',1)[-1].split('LATEND',1)[0];m=re.search(r'rise -> rise.*?^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+) latency$',lat,re.S|re.M)
 return dict(worst=values,latency_rise=[float(m[1]),float(m[2])] if m else None,command=cmd)
probe=sta('TT','probe_TT.log',sdc);ffprobe=sta('FF','probe_FF.log',sdc)
assert probe['latency_rise'] and ffprobe['latency_rise']
tt=probe['latency_rise'];ff=ffprobe['latency_rise'];sdc=out/'actual_tt_ref_25ps.sdc'
cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'physical/hbm_w2_rb_station_20261006/make_sdc.py'),'--period-ps','833.333','--l-min',str(tt[0]),'--l-max',str(tt[1]),'--l-ff-min',str(ff[0]),'--l-ff-max',str(ff[1]),'--hold-skew-ps','25','--out',str(sdc)]
p=subprocess.run(cmd,capture_output=True,text=True);(out/'sdc_generation.log').write_text(p.stdout+p.stderr);p.check_returncode()
results={c:sta(c,f'actual_tt_ref_{c}.log',sdc) for c in ('TT','FF','SS')}
record=dict(schema='opentallas.w2-baseline-tt25.v1',source='fec1faadd784e94926256e0d726ea32b6d6d9714',baseline=str(run),policy='Option B TT setup>=0 FF hold>=0; SS sensitivity; 833.333ps setup60/hold25; all async checks included',baseline_artifact_sha256={str(p.relative_to(run)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (odb,spef,old,run/'signoff.json')},probe_unchanged_io=dict(TT=probe,FF=ffprobe),sdc_generation_command=cmd,actual_tt_ref=results,accept=dict(TT_setup_ps=results['TT']['worst']['max'],FF_hold_ps=results['FF']['worst']['min'],TT_ok=results['TT']['worst']['max']>=0,FF_ok=results['FF']['worst']['min']>=0),historical_failure_preserved=True)
(out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record['accept']),flush=True)
