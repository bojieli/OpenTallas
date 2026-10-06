#!/usr/bin/env python3
"""Real routed LEF + SS/FF timing-model exports, including failed routes.
Never turn an unclosed route into a closed abstract. Preserve every verdict.
"""
import argparse,json,hashlib,subprocess,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--name',required=True);p.add_argument('--NO',type=int,required=True);p.add_argument('--physical',type=Path,required=True);p.add_argument('--image',default='openroad/orfs:asap7lock');a=p.parse_args()
out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);base=a.base.resolve()
sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
required=['6_final.odb','6_final.spef','6_final.sdc','6_final.v']
assert all((base/n).is_file() for n in required),'real terminal route inputs required'
ev=json.loads(a.physical.read_text())
assert ev['design']['top']==a.name and ev['design']['parameters']['NO']==a.NO
assert ev['flow_completed'] and 'pnr' in ev['stages_completed']
rec=dict(name=a.name,NO=a.NO,route_hashes={n:sha(base/n) for n in required},source_record_sha256=sha(a.physical),source_hashes=ev['design']['sources'],parameters=ev['design']['parameters'],tool_image=subprocess.check_output(['docker','image','inspect',a.image,'--format','{{.Id}}'],text=True).strip(),SS_setup_ps=60,FF_hold_ps=25,actual_clock='clk_sm positive; actual four-inverter fclk_o retained',parent_closed=False,die_qualified=False,placeholder=False,corners={},original_acceptance=ev.get('acceptance'))
for corner in ('ss','ff'):
 libs=[f'/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{f}_RVT_{corner.upper()}_nldm_{s}' for f,s in [('AO','211120.lib.gz'),('INVBUF','220122.lib.gz'),('OA','211120.lib.gz'),('SEQ','220123.lib'),('SIMPLE','211120.lib.gz')]]
 tcl='\n'.join(f'read_liberty {{{l}}}' for l in libs)+'''
read_db /route/6_final.odb
read_sdc /route/6_final.sdc
read_spef /route/6_final.spef
set_propagated_clock [all_clocks]
set_units -time ps -capacitance fF
set b [ord::get_db_block]
set f [open /out/pins_CORNER.tsv w]
puts $f "port\tdirection\tnet\treceiver_pin_cap_fF\tsinks"
foreach bt [$b getBTerms] {
 set net [$bt getNet];set cap 0;set sinks {}
 if {$net ne "NULL"} {
  foreach it [$net getITerms] {
   if {[$it isOutputSignal] || [[$it getMTerm] getSigType] in {POWER GROUND}} {continue}
   set ref [[[$it getInst] getMaster] getName];set pin [[$it getMTerm] getName]
   set lp [get_lib_pins -quiet */$ref/$pin]
   if {[llength $lp]!=1} {error "missing actual receiver Liberty $ref/$pin"}
   set cp [get_property $lp capacitance];set cap [expr {$cap+$cp}]
   lappend sinks [list [[$it getInst] getName] $ref $pin $cp]
  }
 }
 puts $f [join [list [$bt getName] [$bt getIoType] [$net getName] $cap $sinks] "\t"]
}
close $f
report_checks -path_delay max -group_path_count 8 -format full_clock_expanded > /out/setup_CORNER.txt
report_checks -path_delay min -group_path_count 8 -format full_clock_expanded > /out/hold_CORNER.txt
report_worst_slack -max
report_worst_slack -min
report_check_types -max_slew -max_capacitance -max_fanout
write_timing_model -library_name NAME_CORNER /out/NAME_CORNER.lib
'''.replace('CORNER',corner).replace('NAME',a.name)
 if corner=='ss':tcl+=f'write_abstract_lef /out/{a.name}.lef\n'
 tcl+='puts OT_STATION_EXPORT_DONE\nexit\n'
 out.joinpath(f'export_{corner}.tcl').write_text(tcl)
 cmd=['docker','run','--rm','-v',f'{base}:/route:ro','-v',f'{out}:/out','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',a.image,'-exit','-no_init','-threads','1',f'/out/export_{corner}.tcl']
 with out.joinpath(f'export_{corner}.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 log=out.joinpath(f'export_{corner}.log').read_text()
 rec['corners'][corner]={'returncode':r.returncode,'done':'OT_STATION_EXPORT_DONE' in log,'source_SPEF_sha256':sha(base/'6_final.spef'),'library_paths':libs}
 out.joinpath('export.json').write_text(json.dumps(rec,indent=2)+'\n')
 if r.returncode or 'OT_STATION_EXPORT_DONE' not in log:raise SystemExit('real station extraction failed '+corner)
 text=out.joinpath(f'{a.name}_{corner}.lib').read_text()
 rec['corners'][corner]['edge_clockQ_arcs']=len(re.findall(r'timing_type\s*:\s*(?:rising_edge|falling_edge)',text))
 rec['corners'][corner]['clock_related_arcs']=len(re.findall(r'related_pin\s*:\s*"clk_sm"',text))
 caps=[]
 for line in out.joinpath(f'pins_{corner}.tsv').read_text().splitlines()[1:]:
  name,direction,net,cap,sinks=line.split('\t',4)
  if direction=='INPUT':
   assert float(cap)>0,'no actual positive input cap '+name
   caps.append((name,float(cap)))
 assert dict(caps).get('clk_sm',0)>0
 assert rec['corners'][corner]['edge_clockQ_arcs']>0
 rec['corners'][corner]['input_caps_fF']=dict(caps)
rec['status']='REAL_ROUTED_SOURCE_LOCAL_VIEWS_PARENT_OPEN'
rec['files']={x.name:sha(x) for x in out.iterdir() if x.is_file()}
out.joinpath('export.json').write_text(json.dumps(rec,indent=2)+'\n')
print(rec['status'])
