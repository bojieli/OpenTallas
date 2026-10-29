#!/usr/bin/env python3
"""Recompose S81 s12 after aligning its shared t1 reset entry with the abutting W output."""
import json,sys,copy,importlib.util
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import schema as S, reset_tree as RT, clock_landing_plan as CL
sp=importlib.util.spec_from_file_location('s12','results/die_s81_19_1028/scripts/recompose_s12.py'); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
inp,tab,out,side=sys.argv[1:5]
raw=json.load(open(inp)); base,clones=m.uncompose(raw)
assert base['reset']['in_sites']['serdes__t1']==[2876.64,1074.016]
old=base['reset']['in_sites']['serdes__t1']
base['reset']['in_sites']['serdes__t1']=[2876.64,460.576]
print('RESET_SITE',old,'->',base['reset']['in_sites']['serdes__t1'],flush=True)
new,sc=CL.compose(base,json.load(open(tab)),plan_path=inp,observer_part=m.OBS_PART,observer=dict(m.OBS))
new['note']+='; CODEX S81 2340: shared serdes__t1 reset entry E1074.016->E460.576 aligned with abutting parent rst_o W460.960; monitor/release network recomposed'
json.dump(new,open(out,'w'),indent=1);json.dump(sc,open(side,'w'),indent=1)
print(json.dumps(dict(types=len(new['partition_types']),edges=len(new['clock']['landing_network']['edges']),collector={k:sc['collector'][k] for k in ('placement_failures','max_die_hop_um','boot_budget')})),flush=True)
