"""Read-only census of pinned protected80a route, no checkpoint mutation."""
import argparse,hashlib,json,pathlib,re,subprocess,sys
import corner_sta as C
ap=argparse.ArgumentParser();ap.add_argument('--original',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);args=ap.parse_args()
r=args.out.resolve();r.mkdir(exist_ok=False);original=next((args.original/'results/asap7').glob('*/base'))
expected={'6_final.odb':'2048753b927320bda6c7aaf5d8660406caeb8181a3b1e345feea953f3763d013','6_final.spef':'25284b2269df516e1410e49cc7d1e057ecd2c3aac2455ec75f0dcbade3de7829','6_final.sdc':'563d458cd497d6ce96a771cdd38714f91852afda138831e1610f9946f999de73'}
base=r/'results/asap7/protected80a/base';base.mkdir(parents=True);inputs=[]
for name,digest in expected.items():
 p=original/name;assert C.sha(p)==digest,(p,'source mismatch')
 (base/name).hardlink_to(p);inputs.append(dict(source=str(p),sha256=digest))
(r/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
bundle=pathlib.Path(__file__).resolve().parent
runs=[];internal=[]
def launch(script,python=False):
 cmd=['docker','run','--rm','-v',f'{r}:/work','-v',f'{bundle}:/bundle:ro','openroad/orfs:asap7lock','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit']
 if python:cmd+=['-python']
 cmd+=[script];p=subprocess.run(cmd,capture_output=True,text=True)
 name=pathlib.Path(script).stem;(r/(name+'.log')).write_text(p.stdout);(r/(name+'.stderr')).write_text(p.stderr)
 runs.append(dict(script=script,rc=p.returncode));(r/'runs.json').write_text(json.dumps(runs,indent=2)+'\n')
 if p.returncode or '[ERROR' in p.stdout or '[ERROR' in p.stderr:raise RuntimeError(f'{script}: rc={p.returncode}')
 return p.stdout
launch('/bundle/topology.py',True)
for corner in ['ff','ss']:
 s=C.script(corner,'/work/results/asap7/protected80a/base',[]);s=s[:s.index('puts "OT_CORNER')]
 s+='''
report_units
foreach port [all_outputs] {
 set name [get_full_name $port]
 foreach check {min max} {
  puts "OT_OUTPUT_BEGIN $name $check"
  report_checks -to $port -path_delay $check -group_path_count 10 -endpoint_path_count 2 -format full_clock_expanded -fields {slew cap fanout input_pins} -digits 4
  puts "OT_OUTPUT_END $name $check"
 }
}
puts "OT_READY_BEGIN"
report_checks -from [get_ports req_ready] -path_delay min_max -group_path_count 10 -endpoint_path_count 4 -format full_clock_expanded -fields {slew cap fanout input_pins} -digits 6
puts "OT_READY_END"
'''
 if corner=='ff':s+='''
foreach pin [all_registers -data_pins] {
 set slack [get_property $pin slack_min]
 if {$slack ne "INF" && $slack < 25.0} {
  puts "OT_INTERNAL_BEGIN [get_full_name $pin] $slack"
  report_checks -to $pin -path_delay min -group_path_count 10 -endpoint_path_count 2 -format full_clock_expanded -fields {slew cap fanout input_pins} -digits 6
  puts "OT_INTERNAL_END"
 }
}
'''
 else:
  for pin in internal:
   assert not any(c in pin for c in '{}\n')
   s+=f'puts "OT_INTERNAL_SS_BEGIN {pin}"\nreport_checks -to [get_pins {{{pin}}}] -path_delay max -group_path_count 10 -endpoint_path_count 2 -format full_clock_expanded -digits 6\nputs "OT_INTERNAL_SS_END"\n'
 s+='exit\n';path=r/f'outputs_{corner}.tcl';path.write_text(s);log=launch('/work/'+path.name)
 if corner=='ff':internal=re.findall(r'OT_INTERNAL_BEGIN (\S+) ',log)
for name,digest in expected.items():assert C.sha(original/name)==digest,'source changed'
(r/'complete.json').write_text(json.dumps(dict(status='PASS',scope='read-only endpoint census, not closure',source='80a11cea9191ca09153367debd21e79bef473605',internal_endpoints_below25=len(internal),scripts={p.name:C.sha(p) for p in bundle.glob('*.py')}),indent=2)+'\n')
