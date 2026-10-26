#!/usr/bin/env python3
"""Repair source-pinned ATT hi placement and measure every actual LEF signal pin.

This proves only component geometry and Manhattan reach. It does not claim
clock timing, blockage-aware routing capacity, external seams or a native engine.
"""
import argparse, copy, hashlib, json
from pathlib import Path

def apply(manifest, plan):
    if manifest['component_sha256'] != plan['source_component_sha256']:
        raise ValueError('component source mismatch')
    result=copy.deepcopy(manifest)
    children={c['instance']:c for c in result['children']}
    if set(plan['placement_overrides_um'])-children.keys(): raise ValueError('unknown child')
    for name, xy in plan['placement_overrides_um'].items():
        child=children[name]; dx,dy=[x-y for x,y in zip(xy,child['xy_um'])]
        for shape in [s for p in child['pins'].values() for s in p['shapes']]+child['obs']:
            x0,y0,x1,y1=shape['rect_um']
            shape['rect_um']=[x0+dx,y0+dy,x1+dx,y1+dy]
        child['xy_um']=xy
    return result

def audit(d):
    cs={c['instance']:c for c in d['children']};W,H=d['outline_um']; overlaps=[];outside=[];offgrid=[]
    for i,a in enumerate(d['children']):
        ax,ay=a['xy_um'];aw,ah=a['outline_um']
        if ax<0 or ay<0 or ax+aw>W+1e-6 or ay+ah>H+1e-6:outside.append(a['instance'])
        if abs(ax/.432-round(ax/.432))>1e-5 or abs(ay/2.16-round(ay/2.16))>1e-5:offgrid.append(a['instance'])
        for b in d['children'][i+1:]:
            bx,by=b['xy_um'];bw,bh=b['outline_um']
            if min(ax+aw,bx+bw)-max(ax,bx)>1e-6 and min(ay+ah,by+bh)-max(ay,by)>1e-6:overlaps.append([a['instance'],b['instance']])
    def points(ep,k):
        pins=cs[ep['instance']]['pins'];bit=ep['lsb']+k
        name=f"{ep['port']}[{bit}]"
        if name not in pins: name=ep['port']
        if name not in pins:raise ValueError('missing actual LEF pin '+str(ep))
        return [((s['rect_um'][0]+s['rect_um'][2])/2,(s['rect_um'][1]+s['rect_um'][3])/2) for s in pins[name]['shapes']]
    groups=[];count=0; multi=[]
    for conn in d['connections']:
        if conn['kind']!='signal':continue
        drivers=[e for e in conn['endpoints'] if e['direction']=='output']
        loads=[e for e in conn['endpoints'] if e['direction']=='input']
        if not drivers:continue # external input, not an internal connection
        if len(drivers)!=1:multi.append(conn['net']);continue
        driver=drivers[0]
        for load in loads:
            if load['width']!=driver['width']:raise ValueError('bus width mismatch')
            distances=[min(abs(a[0]-b[0])+abs(a[1]-b[1]) for a in points(driver,k) for b in points(load,k)) for k in range(load['width'])]
            count+=len(distances)
            groups.append({'net':conn['net'],'driver':driver['instance']+'.'+driver['port'],'load':load['instance']+'.'+load['port'],'bits':load['width'],'max_manhattan_um':round(max(distances),6)})
    worst=sorted(groups,key=lambda x:x['max_manhattan_um'],reverse=True)
    return dict(children=len(cs),checked_signal_pin_pairs=count,internal_groups=len(groups),overlaps=overlaps,outside=outside,offgrid=offgrid,multiple_driver_nets=multi,max_manhattan_um=worst[0]['max_manhattan_um'],over_500um=[x for x in worst if x['max_manhattan_um']>500],worst_groups=worst[:20],geometry_reach_pass=not(overlaps or outside or offgrid or multi) and worst[0]['max_manhattan_um']<=500)

def main():
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('plan',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--emit',type=Path);a=p.parse_args()
    raw=a.manifest.read_bytes();d=json.loads(raw);plan=json.loads(a.plan.read_text())
    if hashlib.sha256(raw).hexdigest()!=plan['baseline_direct_manifest_sha256']:raise ValueError('manifest bytes mismatch')
    fixed=apply(d,plan);before=audit(d);after=audit(fixed)
    mutant=copy.deepcopy(fixed);c=next(x for x in mutant['children'] if x['instance']=='g_mt.u_mt')
    # Actual central merge input geometry mutation must break measured reach.
    for pin in c['pins'].values():
        for s in pin['shapes']:
            s['rect_um'][0]+=1000;s['rect_um'][2]+=1000
    mutated=audit(mutant)
    result=dict(schema='opentallas.hbm_attention.reach_evidence.v1',source_manifest_sha256=hashlib.sha256(raw).hexdigest(),plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),before=before,after=after,merge_pin_shift_mutant_detected=bool(mutated['over_500um']),native_qualified=False,limits=plan['qualification']['unresolved'])
    if not after['geometry_reach_pass'] or not result['merge_pin_shift_mutant_detected']:raise ValueError('repair or mutant audit failed')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    if a.emit:a.emit.write_text(json.dumps(fixed,indent=1)+'\n')
    print(f"PASS {before['max_manhattan_um']} -> {after['max_manhattan_um']} um, {after['checked_signal_pin_pairs']} pin pairs, mutant detected; geometry only")
if __name__=='__main__':main()
