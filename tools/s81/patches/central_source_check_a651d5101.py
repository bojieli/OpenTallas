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
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    m.ROOT=root
    return m
q=load('qwen_rom_fulldie',base/'qwen_a651d5101.py')
f=load('dsrom_s81_fulldie',base/'generator_a651d5101.py')
r=load('recipe',base/'recipe_a651d5101.py')
r.OUT=base/'central_a651d5101_generation'
assert f.HOST_SLAB is False and f.HOST_MM2 == .1
for name in ('scan','headp2'):
    record=r.plan(name,r.recipes()[name])
    print(json.dumps(dict(source_commit='a651d5101',name=name,
        fits=record.get('recipe',record).get('fits'),error=record.get('error'),
        scope='current central Python sources; immutable fe365 physical inputs; generation only')),flush=True)
