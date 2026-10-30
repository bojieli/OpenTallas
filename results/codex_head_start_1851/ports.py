import json,sys
from pathlib import Path
repo,plan,stages,physical,out=map(Path,sys.argv[1:]);sys.path[:0]=[str(repo/'tools/die_plan')]
import schema,reset_tree
p=schema.Plan(json.load(open(plan)),plan);s=json.load(open(stages));ph=json.load(open(physical));ports={}
for n,q in s['reset_ports'].items():ports[n]=dict(xy_um=q['xy_um'],layer='M7',source_kind='registered_wavefront',source=q)
for q in s['die_outputs']:
    part=q['dst_part'];xy=p.to_die(part,reset_tree.start_in_pin(p,p.parts[part]['type']))
    ports[q['net']]=dict(xy_um=xy,layer='M7',source_kind='actual_partition_start_pin',part=part)
ph['ports']=ports;ph['reset_form']='local_wavefront'
assert not out.exists();out.write_text(json.dumps(ph,indent=1))
print(json.dumps(dict(ports=len(ports),reset_ports=len(s['reset_ports']),die_outputs=len(s['die_outputs']))))
