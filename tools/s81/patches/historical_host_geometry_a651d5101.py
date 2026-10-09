import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

base=Path('/srv/opentallas-scratch/claude/s81-dies')
root=base/'src_fe365cd13'
sys.path.insert(0,str(root/'tools'))
os.environ['OT_S81_Q_LEF']='physical/s81_die_views/q_elem_qs5f/q_elem.lef.gz'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);m.ROOT=root
    return m
q=load('qwen_rom_fulldie',base/'qwen_a651d5101.py')
f=load('dsrom_s81_fulldie',base/'generator_a651d5101.py')
ap=f.die_options(argparse.ArgumentParser())
opts=(base/'central_a651d5101_generation/scan/options.txt').read_text().split()
f.apply_options(ap.parse_args(opts))
# Exact initial placement pass, before any global hop stations. This is
# geometry extraction from historical synthetic HOST, not a native successor.
f.HOP_PLAN={}
m=f.build_r8()
points=dict(failed_previous=[13443.396,15411.588],failed_nominal=[11954.6,15372.7],
            source=[13959.936,15372.72],destination=[7134.912,1331.628])
def box(it):
    return [it.x,it.y,it.x+it.w,it.y+it.h]
def overlaps(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
envelope=[points['failed_previous'][0]-800,points['failed_previous'][1]-800,
          points['failed_previous'][0]+800,points['failed_previous'][1]+800]
local=[dict(name=i.name,master=i.master,kind=i.kind,box=box(i),region=i.region)
       for i in m['insts'] if overlaps(box(i),envelope)]
record=dict(source_commit='a651d5101',inputs_commit='fe365cd13',scope='exact initial placement metadata, before global hop stations; synthetic HOST buses retained only as history',
            source_options=opts,outline=f.DIE,geometry={k:v for k,v in m['geo'].items() if not callable(v)},corridors=f._corridors(m),
            historical_failure_points=points,local_occupancy=local,
            slabs=[dict(name=i.name,master=i.master,box=box(i),kind=i.kind,region=i.region)
                   for i in m['insts'] if i.region in ('spine','band','hub') or i.name.startswith(('ctrl_','svc_','phy_'))],
            all_occupancy=[dict(name=i.name,box=box(i),kind=i.kind,region=i.region) for i in m['insts']],
            native_packet_width=None,native_endpoint_binding=None,adopted=False)
out=base/'host_corridor_geometry_a651d5101_v2.json'
assert not out.exists()
out.write_text(json.dumps(record,indent=1))
print(json.dumps(dict(instances=len(m['insts']),local_blockers=len(local),output=str(out),scope=record['scope'])),flush=True)
