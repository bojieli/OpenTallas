#!/usr/bin/env python3
"""Private NL parent adoption artifact. Never edits a POR, native DB or pin."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('lef_clock_entry',ROOT/'tools/die_plan/lef_clock_entry.py')
G=importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
WINDOWS={6:(228.869,578.820,229.071,578.980),7:(228.880,578.432,229.040,579.328)}
SITE=(699.840,77.772,'MY')
FOOTPRINTS={5:[(928.764,656.645,928.788,656.699)],
            6:[(928.753,656.656,928.827,656.688)],
            7:[(928.784,656.268,928.816,657.036)]}


def subtract(a,b):
    x0,y0,x1,y1=a; u0,v0,u1,v1=b
    u0,v0,u1,v1=max(x0,u0),max(y0,v0),min(x1,u1),min(y1,v1)
    if u0>=u1 or v0>=v1:
        return [a]
    return [r for r in [(x0,y0,u0,y1),(u1,y0,x1,y1),(u0,y0,u1,v0),(u0,v1,u1,y1)]
            if r[0]<r[2] and r[1]<r[3]]


def abstract(text):
    out=[]; inobs=False; layer=None; cuts=0
    for line in text.splitlines():
        stripped=line.strip()
        if stripped=='OBS': inobs=True
        elif inobs and stripped.startswith('END'): inobs=False
        if inobs:
            lm=re.fullmatch(r'LAYER M(\d+)\s*;',stripped)
            if lm: layer=int(lm.group(1))
            if layer in WINDOWS and stripped.startswith('RECT '):
                vals=stripped.split()[1:-1]
                if len(vals)!=4: raise ValueError('unsupported OBS RECT')
                a=tuple(map(float,vals)); pieces=subtract(a,WINDOWS[layer])
                if pieces!=[a]: cuts+=1
                out.extend('      RECT '+' '.join(f'{x:.6f}' for x in r)+' ;' for r in pieces)
                continue
        out.append(line)
    if cuts != 2: raise ValueError(f'expected exactly two blanket OBS cuts, got {cuts}')
    result='\n'.join(out)+'\n'
    # All original PIN blocks must remain byte-identical.
    pins=lambda s: re.findall(r'^  PIN .*?^  END [^\n]+',s,re.M|re.S)
    if pins(text)!=pins(result): raise ValueError('PIN mutation forbidden')
    return result


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--lef',type=Path,required=True)
    ap.add_argument('--pins',type=Path,required=True); ap.add_argument('--plan',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists(): raise ValueError('new output directory required')
    original=a.lef.read_text(); candidate=abstract(original)
    blocks,target,size=G.geometry(candidate,'qfd_tile_nl_a0c','ck',7,SITE)
    if not G.entry_clear(FOOTPRINTS,blocks,target,7): raise ValueError('access witness blocked')
    oldblocks,oldtarget,_=G.geometry(original,'qfd_tile_nl_a0c','ck',7,SITE)
    if G.entry_clear(FOOTPRINTS,oldblocks,oldtarget,7): raise ValueError('uncut blanket unexpectedly clear')
    plan=json.loads(a.plan.read_text()); types=[]; instances=[]
    for name,t in plan['partition_types'].items():
        for core in t.get('hard_cores',[]):
            if core.get('module')=='qfd_tile_nl_a0c':
                types.append(name)
                if core['inst']!='u_t30': raise ValueError('unexpected NL instance')
    parts=plan.get('partitions',plan.get('instances',{}))
    if isinstance(parts,dict): instances=[n for n,p in parts.items() if p.get('type') in types]
    elif isinstance(parts,list): instances=[p.get('name',p.get('inst')) for p in parts if p.get('type') in types]
    record=dict(status='PRIVATE_SOURCE_WITNESS_ONLY',default_activation=False,
        source_base='66d55c026ad',params={'IDLE_UCK':1},types=types,instances=instances,
        original_lef_sha256=hashlib.sha256(original.encode()).hexdigest(),
        access_lef_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
        clock_pin={'name':'ck','layer':'M5','native_rect':[228.948,578.640,228.996,579.120]},
        native_obs_windows=WINDOWS,parent_site=SITE,parent_conductor_footprints=FOOTPRINTS,
        clock_tap_old=[699.936,745.848],clock_tap_new=[928.800,656.652],
        delta_from_old=[228.864,-89.196],data_cycle_delta=0,
        native_evidence='I1 codex-qc-nl-adoption-1551/access_roi/native_roi.json; measured ALL foreign native ROI shapes incl PG/fill',
        signed_mean_clock_ps={'TT':774.38,'FF':610.59},
        obligations=['emit and verify actual parent VIA56/M6 bridge/VIA67/M7 entry',
            'protect real M5 pin and parent PG clearance; no child DB or PIN change',
            'source-only entry mechanism plus actual-state kit guard before physical pilot',
            'parent clock route/STA/DRC/supply and strict bind with explicit IDLE_UCK=1',
            'owner adoption of both parent types and affected instances; no POR activation here'])
    pins=json.loads(a.pins.read_text())
    clock=[r for r in pins['pins'] if r.get('name')=='ck']
    if len(clock)!=1 or (clock[0]['layer'],clock[0]['x'],clock[0]['y'])!=('M4',457.824,668.076):
        raise ValueError('unexpected old planned clock pin')
    clock[0].update(layer='M5',x=228.972,y=578.880)
    delta=[]
    access={'pin':'ck','footprints_um':{f'M{k}':v for k,v in FOOTPRINTS.items()}}
    for name in types:
        typ=plan['partition_types'][name]
        ci=next(i for i,c in enumerate(typ['hard_cores']) if c.get('module')=='qfd_tile_nl_a0c')
        core=typ['hard_cores'][ci]
        if core.get('params'):
            raise ValueError('existing child parameters require explicit preservation')
        ti=next(i for i,t in enumerate(typ['clock']['taps']) if t.get('name')=='u_t30.ck')
        prefix='/partition_types/'+name
        delta.extend([
            {'op':'test','path':prefix+'/hard_cores/'+str(ci)+'/pins_file','value':core['pins_file']},
            {'op':'add','path':prefix+'/hard_cores/'+str(ci)+'/params','value':{'IDLE_UCK':1}},
            {'op':'add','path':prefix+'/hard_cores/'+str(ci)+'/clock_entry_access','value':access},
            {'op':'replace','path':prefix+'/hard_cores/'+str(ci)+'/pins_file',
             'value':f'results/physical/qc_nl_clock_adoption_1551/{a.out.name}/a0_nl_pins.json'},
            {'op':'test','path':prefix+'/clock/taps/'+str(ti)+'/xy','value':[699.936,745.848]},
            {'op':'replace','path':prefix+'/clock/taps/'+str(ti)+'/xy','value':[928.800,656.652]},
            {'op':'replace','path':prefix+'/clock/taps/'+str(ti)+'/insertion_ps','value':774.38},
            {'op':'replace','path':prefix+'/clock/taps/'+str(ti)+'/insertion_ff_ps','value':610.59},
            {'op':'replace','path':prefix+'/clock/taps/'+str(ti)+'/budget_owner',
             'value':'private candidate: accepted NL signed pin-flop mean TT774.38/FF610.59; parent STA unqualified'}])
    record['activation_blockers']=['private access LEF must be paired with unchanged accepted Liberty using an honest derived-view receipt; current view_lef may select the original blanket export',
        'parent PG cut and exact native-access-window review; no source or current plan mutation']
    record['patch_semantics']='private proposed event only; budget uses actual accepted signed means, no synthesized max-clock-path substitution'
    a.out.mkdir(parents=True)
    (a.out/'a0_nl_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    (a.out/'proposed_event.patch.json').write_text(json.dumps(delta,indent=2)+'\n')
    (a.out/'qfd_tile_nl_a0c.access.lef').write_text(candidate)
    (a.out/'adoption.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'witness':'PASS','types':types,'instances':len(instances),'activation':False}))

if __name__=='__main__': main()
