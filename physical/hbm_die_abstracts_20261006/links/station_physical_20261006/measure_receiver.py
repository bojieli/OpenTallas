#!/usr/bin/env python3
"""Measure real selected mapped receiver pin loads at SS and FF.
Source-local repeated-station characterization, not unknown installed SM/die RC.
"""
import argparse,subprocess,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--mapped',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--src',type=Path,required=True);p.add_argument('--image',default='openroad/orfs:asap7lock');a=p.parse_args()
out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
libs={'ss':['AO','INVBUF','OA','SEQ','SIMPLE'],'ff':['AO','INVBUF','OA','SEQ','SIMPLE']}
stamps={'AO':'211120.lib.gz','INVBUF':'220122.lib.gz','OA':'211120.lib.gz','SEQ':'220123.lib','SIMPLE':'211120.lib.gz'}
for corner in ('ss','ff'):
 files=[f'/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{family}_RVT_{corner.upper()}_nldm_{stamps[family]}' for family in libs[corner]]
 tcl='\n'.join('read_liberty {'+s+'}' for s in files)+'''
read_verilog /mapped.v
link_design ot_hbm_native_frame_station
set_units -time ps -capacitance fF
set f [open /out/caps_CORNER.tsv w]
puts $f "port\tcap_fF\tsink_count\tsinks"
foreach p [all_inputs] {
 set cap 0;set sinks {};set pin_count 0
 foreach pin [get_fanout -from $p -flat -pin_levels 1 -trace_arcs all] {
  if {[get_property $pin direction] ne "input"} {continue}
  set cs [get_cells -of_objects $pin]
  if {[llength $cs]!=1} {continue}
  set ref [get_property $cs ref_name]
  set name [lindex [split [get_full_name $pin] /] end]
  set lp [get_lib_pins -quiet */$ref/$name]
  if {[llength $lp]!=1} {continue}
  set c [get_property $lp capacitance]
  set cap [expr {$cap+$c}];incr pin_count;lappend sinks [list [get_full_name $pin] $ref $c]
 }
 if {$cap<=0} {error "no actual positive receiver cap [get_full_name $p]"}
 puts $f [join [list [get_full_name $p] $cap $pin_count $sinks] "\t"]
}
close $f
puts OT_RECEIVER_CAPS_DONE
exit
'''.replace('CORNER',corner)
 out.joinpath(f'caps_{corner}.tcl').write_text(tcl)
 cmd=['docker','run','--rm','-v',f'{a.mapped.resolve()}:/mapped.v:ro','-v',f'{out}:/out','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta',a.image,'-exit','-no_init',f'/out/caps_{corner}.tcl']
 with out.joinpath(f'caps_{corner}.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode or 'OT_RECEIVER_CAPS_DONE' not in out.joinpath(f'caps_{corner}.log').read_text():raise SystemExit(f'actual receiver cap extraction failed {corner}')
 tables={}
 for line in out.joinpath(f'caps_{corner}.tsv').read_text().splitlines()[1:]:
  name,cap,count,sinks=line.split('\t',3);tables[name]=float(cap)
 out.joinpath(f'caps_{corner}.json').write_text(json.dumps(tables,indent=2)+'\n')
manifest={'source_mapped_sha256':hashlib.sha256(a.mapped.read_bytes()).hexdigest(),'tool':'actual OpenSTA shipped in ORFS26Q3 image; no geometry invented','image':subprocess.check_output(['docker','image','inspect',a.image,'--format','{{.Id}}'],text=True).strip(),'time_unit':'ps','cap_unit':'fF','context':'measured source-local adjacent copy, external SM/die routing OPEN','corner_files':{n:hashlib.sha256(out.joinpath(n).read_bytes()).hexdigest() for n in ['caps_ss.tsv','caps_ff.tsv','caps_ss.json','caps_ff.json']}}
out.joinpath('receiver.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Actual SS/FF selected receiver pin caps measured')
