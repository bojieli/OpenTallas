#!/usr/bin/env python3
"""Place HEAD crossing constant pins in declared macro-free soft area; no cycle changes."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
import gen_phys as G
import schema as S


def apply(raw, plan_path, repo, types=None):
    raw=copy.deepcopy(raw)
    P=S.Plan(raw, path=plan_path)
    report={}
    for tn,t in P.types.items():
        if types is not None and tn not in types: continue
        straps=t.get('count_straps',[])
        if not straps: continue
        if any(s.get('sites_um') for s in straps):
            raise ValueError(f'{tn}: count sites already placed')
        w,h=t['outline_um']; blocked=[]
        for inst,mod,lef,lib,x,y,orient in G.type_macros(P,tn):
            text=(Path(repo)/lef).read_text()
            m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',text)
            if not m:raise ValueError(f'{tn}: no actual LEF size {lef}')
            mw,mh=map(float,m.groups())
            if orient in ('R90','R270','E','W','FE','FW','MXR90','MYR90'):mw,mh=mh,mw
            # Keep the whole 1.92um-tall M5 pin beyond the 4.32um macro halo.
            blocked.append([x-5.4,y-5.4,x+mw+5.4,y+mh+5.4])
        for r in t.get('clock',{}).get('reserved_sites_um',[]):
            x0,y0,x1,y1=r['rect_um'];blocked.append([x0-1.08,y0-1.08,x1+1.08,y1+1.08])
        records=G.plan_pin_records(P,tn,G.type_pins(P,tn))
        occupied=[(r['x'],r['y']) for r in records]
        anchors=[tuple(r['rect_um'][i]/2+r['rect_um'][i+2]/2 for i in (0,1))
                 for r in t.get('clock',{}).get('reserved_sites_um',[]) if r.get('kind')=='landing_ring_bank']
        ax,ay=anchors[0] if anchors else t.get('clock',{}).get('tap_um',[w/2,h/2])
        candidates=[]
        for ix in range(2,int(w/4.32)-1):
            x=round(ix*4.32,4)
            for iy in range(2,int(h/4.32)-1):
                y=round(iy*4.32,4)
                if any(a<=x<=c and b<=y<=d for a,b,c,d in blocked):continue
                candidates.append((abs(x-ax)+abs(y-ay),x,y))
        candidates.sort()
        needed=sum(s['width'] for s in straps);sites=[]
        for _d,x,y in candidates:
            if any(abs(x-a)<2.16 and abs(y-b)<2.16 for a,b in occupied):continue
            sites.append([x,y]);occupied.append((x,y))
            if len(sites)==needed:break
        if len(sites)!=needed:raise ValueError(f'{tn}: no room for {needed} count pins')
        cursor=0
        for s in straps:
            s['layer']='M5';s['sites_um']=sites[cursor:cursor+s['width']];cursor+=s['width']
        report[tn]=dict(pins=needed,layer='M5',macro_halo_um=4.32,pin_extent_margin_um=1.08,pitch_um=4.32,
                        anchor_um=[ax,ay],max_anchor_hop_um=max(abs(x-ax)+abs(y-ay) for x,y in sites))
    return raw,report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    a=ap.parse_args();raw,report=apply(json.loads(a.plan.read_text()),a.plan,a.repo)
    errors=S.validate(raw)
    if errors:raise ValueError(errors[:10])
    a.out.write_text(json.dumps(raw,indent=1)+'\n')
    a.out.with_suffix('.count_sites.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
