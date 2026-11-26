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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_count_strap_reach as R

PITCH_UM = 4.32


def seat_groups(groups, w, h, blocked, occupied, pitch=PITCH_UM):
    """C-STRAP-REACH: seat each group (name, width, (ax, ay)) on the M5 pitch grid at the free sites nearest its own anchor.
    blocked [x0,y0,x1,y1] rects, occupied [(x, y)] pin centres (updated in place); -> {name: [[x, y], ...]}; raises when no room."""
    nx, ny = int(w / pitch) - 1, int(h / pitch) - 1
    out = {}
    for name, width, (ax, ay) in groups:
        # only the window around the anchor can hold the nearest sites; widen it until enough free sites are found
        rad, sites = 12, []
        while True:
            ix0, ix1 = max(2, int(ax / pitch) - rad), min(nx, int(ax / pitch) + rad + 1)
            iy0, iy1 = max(2, int(ay / pitch) - rad), min(ny, int(ay / pitch) + rad + 1)
            cand = sorted((abs(round(ix * pitch, 4) - ax) + abs(round(iy * pitch, 4) - ay), round(ix * pitch, 4), round(iy * pitch, 4))
                          for ix in range(ix0, ix1) for iy in range(iy0, iy1))
            sites = []
            for d, x, y in cand:
                if any(a <= x <= c and b <= y <= e for a, b, c, e in blocked):
                    continue
                if any(abs(x - a) < 2.16 and abs(y - b) < 2.16 for a, b in occupied):
                    continue
                sites.append((x, y))
                if len(sites) == width:
                    break
            # a window is exact for the nearest sites only while the width-th site is inside the inscribed diamond of the window
            if len(sites) == width and abs(sites[-1][0] - ax) + abs(sites[-1][1] - ay) <= rad * pitch:
                break
            if ix0 == 2 and iy0 == 2 and ix1 == nx and iy1 == ny:
                break
            rad *= 2
        if len(sites) != width:
            raise ValueError(f"{name}: no room for {width} count pins near {ax:.1f},{ay:.1f}")
        occupied.extend(sites)
        out[name] = [list(p) for p in sites]
    return out


def apply(raw, plan_path, repo, types=None, reach=False, pub=None):
    raw=copy.deepcopy(raw)
    P=S.Plan(raw, path=plan_path)
    report={}
    for tn,t in P.types.items():
        if types is not None and tn not in types: continue
        straps=t.get('count_straps',[])
        if not straps: continue
        move=None
        if reach:
            # C-STRAP-REACH (opt-in): every group seated at its own load cluster; keeps groups that already reach theirs
            txt=R.pub_text(plan_path,t,pub)
            if txt is None:raise ValueError(f'{tn}: no published RTL for reach anchors')
            anch=R.group_anchors(t,txt)
            rows={r['strap']:r for r in R.group_findings(t,anch)}
            move=[s for s in straps if rows[s['name']]['status'] in ('REPRODUCE','NOSEAT')]
            if not move:continue
            for s in move:s.pop('sites_um',None);s.pop('layer',None)
        elif any(s.get('sites_um') for s in straps):
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
        if reach:
            before={s['name']:rows[s['name']] for s in move}
            seated=seat_groups([(s['name'],s['width'],anch[s['name']][:2]) for s in move],w,h,blocked,occupied)
            for s in move:s['layer']='M5';s['sites_um']=seated[s['name']]
            report[tn]=dict(mode='reach',groups={s['name']:dict(anchor=[round(v,3) for v in anch[s['name']][:2]],source=anch[s['name']][2],
                            before_dmax_um=before[s['name']]['dmax'],before_status=before[s['name']]['status'],sites_um=seated[s['name']],
                            after_dmax_um=round(max(abs(x-anch[s['name']][0])+abs(y-anch[s['name']][1]) for x,y in seated[s['name']]),2)) for s in move})
            continue
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
    ap.add_argument('--reach',action='store_true',help='C-STRAP-REACH: reseat every REPRODUCE/NOSEAT group at its own load cluster (default off)')
    ap.add_argument('--pub',type=Path);ap.add_argument('--types',default='')
    ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    a=ap.parse_args();raw,report=apply(json.loads(a.plan.read_text()),a.plan,a.repo,set(filter(None,a.types.split(','))) or None,a.reach,a.pub)
    errors=S.validate(raw)
    if errors:raise ValueError(errors[:10])
    a.out.write_text(json.dumps(raw,indent=1)+'\n')
    a.out.with_suffix('.count_sites.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
