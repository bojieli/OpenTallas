#!/usr/bin/env python3
"""Audit all actual incident source pin bits for a candidate home change.

Geometry only: no centroid substitution, relay/clock/static timing claim or view
adoption. JSON output includes every missing numeric endpoint and overlap.
"""
import argparse,json,math,re
from pathlib import Path

def audit(model,homes):
    inst={q['n']:dict(q)for q in model['insts']}
    for n,home in homes.items():inst[n].update(home)
    pinmap={m:{p['name']:p for p in q['pins']}for m,q in model['masters'].items()}
    missing=[];links=[]
    def xy(i,p,k):
        q=inst[i];mn=q['m'];name=f'{p}[{k}]'
        # Exported names may be physical fragments or actual source pins.
        pp=pinmap[mn].get(name)
        if pp is None:
            j=model.get('port_join',{}).get(mn,{}).get(p)
            if j:pp=pinmap[mn].get(f'{j[0]}[{j[1][k]}]')
        if pp is None:
            missing.append(dict(instance=i,port=p,bit=k));return None
        r=pp['rect'];x=(r[0]+r[2])/2;y=(r[1]+r[3])/2
        if q['o']in('MY','R180'):x=q['w']-x
        if q['o']in('MX','R180'):y=q['h']-y
        return q['x']+x,q['y']+y
    for b in model['buses']:
        if not any(i in homes for i,p in b['e']):continue
        lengths=[]
        for k in range(b['n']):
            pts=[xy(i,p,k)for i,p in b['e']]
            if any(p is None for p in pts):continue
            # Audit each real source-to-sink branch, including fanouts.
            for p in pts[1:]:lengths.append(abs(pts[0][0]-p[0])+abs(pts[0][1]-p[1]))
        links.append(dict(bus=b['b'],kind=b['c'],bits=b['n'],sinks=len(b['e'])-1,
            max_pin_L1_um=max(lengths)if lengths else None,
            sum_bit_branch_L1_um=sum(lengths),endpoints=b['e']))
    overlap=[]
    vv=list(inst.values())
    for n in homes:
        a=inst[n]
        for b in vv:
            if a['n']>=b['n']and b['n']in homes or a['n']==b['n']:continue
            if a['x']<b['x']+b['w']and a['x']+a['w']>b['x']and a['y']<b['y']+b['h']and a['y']+a['h']>b['y']:
                overlap.append([a['n'],b['n']])
    links.sort(key=lambda z:-(z['max_pin_L1_um']or 0))
    return dict(scope='all incident actual numeric source-pin branches, geometry only',homes=homes,
        complete_numeric_pins=not missing,missing_pins=missing,overlaps=overlap,links=links,
        all_data_bit_branch_L1_um=sum(z['sum_bit_branch_L1_um']for z in links if z['kind']not in('clock_trunk','reset')),
        clock_phase_and_registered_reach='OPEN: geometry does not authorize long unregistered nets')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model',type=Path);p.add_argument('homes',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    a.out.write_text(json.dumps(audit(json.loads(a.model.read_text()),json.loads(a.homes.read_text())),indent=1)+'\n')
if __name__=='__main__':main()
