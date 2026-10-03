#!/usr/bin/env python3
"""Enforce selected v1 W6 plan's new-launch entrypoint; prepare argv only.

This helper never starts a physical driver. Abstract gate-only replay uses the
parent's source-pinned tools. Actual census and SS/FF remain separate gates.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECORD=ROOT/'results/uarch/hbm_W6_contextual_plan_20261003/r2_guarded_launcher/binding.json'

def require(ok,msg):
    if not ok:raise ValueError(msg)

def prepare(parent_root,driver_argv):
    parent_root=Path(parent_root);record=json.loads(RECORD.read_text())
    for path,h in record['source_sha256'].items():
        require(hashlib.sha256((parent_root/path).read_bytes()).hexdigest()==h,'guarded parent source pin '+path)
    require('--macro-track-gate' not in driver_argv and '--gate-only' not in driver_argv,'wrapper controls gate flags')
    specs=[]
    for i,t in enumerate(driver_argv):
        if t=='--macro-view':
            require(i+1<len(driver_argv),'missing macro view');specs.append(driver_argv[i+1])
        elif t.startswith('--macro-view='):specs.append(t.split('=',1)[1])
    require(specs,'actual macro master list required; empty source context refused')
    masters=[]
    for spec in specs:
        name,sep,path=spec.partition('=');require(sep and name and path,'macro view syntax')
        require(path=='physical/asap7_memory_macros/'+name,'selected original v1 geometry; any other selection requires new model')
        masters.append(name)
    require(len(masters)==len(set(masters)),'duplicate requested master')
    require('ot_sram_1r1w_128x256_m1_r2c2' in masters and 'ot_sram_1r1w_1024x256_m2_r2c2' in masters,'source-sized RF andscratch masters')
    argv=['python3',str(parent_root/record['mandatory_launcher']),'--macro-track-gate',*driver_argv]
    return dict(argv=argv,source_binding=record['parent_source'],geometry='original_v1',
                launch_executed=False,launch_ready=False,aligned_actual_placement_hook_required=True,
                complete_placed_instance_census=False,SSFF_qualified=False)
