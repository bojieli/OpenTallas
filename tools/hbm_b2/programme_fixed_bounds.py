"""Unconstrained per-FF minimax bounds against fixed native macro/ABI pins.

FF/FF endpoints are deliberately not fixed in this bound. A >405 result proves
the current fixed-pin geometry needs a physical/source change; a smaller bound
does not prove legal row capacity, shared placement, routing or timing.
"""
import argparse
import csv
import json
import re
from collections import Counter,defaultdict
from pathlib import Path


def plain(name):return name.replace('\\[','[').replace('\\]',']')


def feasible(boxes,r):
    xl=max(b[0]-r for b in boxes);xh=min(b[2]+r for b in boxes)
    yl=max(b[1]-r for b in boxes);yh=min(b[3]+r for b in boxes)
    ul=max(b[0]+b[1]-r for b in boxes);uh=min(b[2]+b[3]+r for b in boxes)
    vl=max(b[0]-b[3]-r for b in boxes);vh=min(b[2]-b[1]+r for b in boxes)
    if xl>xh or yl>yh or ul>uh or vl>vh:return None
    lo=max(yl,xl-vh,ul-xh,(ul-vh)/2);hi=min(yh,uh-xl,xh-vl,(uh-vl)/2)
    if lo>hi+1e-9:return None
    y=(lo+hi)/2;xlo=max(xl,ul-y,vl+y);xhi=min(xh,uh-y,vh+y)
    if xlo>xhi+1e-8:return None
    return [(xlo+xhi)/2,y]


def main():
    p=argparse.ArgumentParser();p.add_argument('--edges',type=Path,required=True)
    p.add_argument('--rows',type=Path,required=True);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--ingress',type=Path,required=True);p.add_argument('--macro-lef',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rows={r['cell']:r for r in csv.DictReader(a.rows.open())};model=json.loads(a.model.read_text())
    macro={r['name']:r for r in model['macros']};masters=json.loads(a.ingress.read_text())['FF_native_pin_masters']
    lp={};lef=a.macro_lef.read_text()
    for m in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',lef,re.S):
        rects=[list(map(float,x))for x in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',m[2])]
        if rects:lp[m[1]]=rects
    def fixed_macro(owner,pin):
        x,y,_,_=macro[plain(owner)]['rect_um'];return [[x+u,y+v,x+U,y+V]for u,v,U,V in lp[plain(pin)]]
    def pin_offset(ff,pin):
        m=masters[rows[ff]['master']];rs=m['pins'][plain(pin)]
        rs=rs+[[u,m['h']-V,U,m['h']-v]for u,v,U,V in rs]
        return [min(x[0]for x in rs)-m['w']/2,min(x[1]for x in rs)-m['h']/2,
                max(x[2]for x in rs)-m['w']/2,max(x[3]for x in rs)-m['h']/2]
    groups=defaultdict(list)
    def add(ff,pin,fixed,role,owner,target_pin):
        ff=plain(ff);offset=pin_offset(ff,pin)
        box=[min(z[0]for z in fixed)-offset[2],min(z[1]for z in fixed)-offset[3],
             max(z[2]for z in fixed)-offset[0],max(z[3]for z in fixed)-offset[1]]
        groups[ff].append(dict(role=role,target=plain(owner),pin=plain(target_pin),reference_box_um=box))
    for e in csv.DictReader(a.edges.open()):
        sk,tk=e['launch_kind'],e['capture_kind']
        if sk=='ff' and tk=='macro':
            add(e['launch_owner'],e['launch_pin'],fixed_macro(e['capture_owner'],e['capture_pin']),
                'FF_to_native_macro',e['capture_owner'],e['capture_pin'])
        elif sk=='macro' and tk=='ff':
            add(e['capture_owner'],e['capture_pin'],fixed_macro(e['launch_owner'],e['launch_pin']),
                'native_macro_to_FF',e['launch_owner'],e['launch_pin'])
    for ff,r in rows.items():
        if r['planned_output_pin_x_um']:
            x,y=float(r['planned_output_pin_x_um']),float(r['planned_output_pin_y_um'])
            add(ff,'QN',[[x,y,x,y]],'FF_to_proposed_ABI_output',ff.split('$_')[0],ff.split('$_')[0])
    bounds=[]
    for ff,cs in sorted(groups.items()):
        boxes=[c['reference_box_um']for c in cs];lo,hi=0.,sum(model['outline_um'])
        for _ in range(42):
            mid=(lo+hi)/2
            if feasible(boxes,mid)is None:lo=mid
            else:hi=mid
        bounds.append(dict(FF=ff,constraints=cs,unconstrained_optimistic_minimax_um=hi,
                           candidate_centre_um=feasible(boxes,hi+1e-7),impossible405=(hi>405+1e-6)))
    bad=[x for x in bounds if x['impossible405']]
    out=dict(status='FAIL_FIXED_PIN_SINGLE_FF405_LOWER_BOUND'if bad else'NECESSARY_FIXED_PIN_BOUNDS_ONLY',
       FF_with_fixed_pin_constraints=len(bounds),impossible405=len(bad),
       max_unconstrained_minimax_um=max(x['unconstrained_optimistic_minimax_um']for x in bounds),
       highest_bounds=sorted(bounds,key=lambda x:x['unconstrained_optimistic_minimax_um'],reverse=True)[:40],
       scope='Fixed native macro pins and current proposed ABI output pins only; all intermediate FFs and orientations unconstrained. Reference boxes conservatively include pin-union gaps.',
       held=['No legal row/global capacity/FF-FF/routing/STA qualification','A<=405 lower bound is not a placement PASS','ABI output windows remain explicit replannable physical proposals'])
    (a.out/'fixed_pin_bounds.json').write_text(json.dumps(out,indent=2)+'\n')
    (a.out/'all_fixed_pin_constraints.json').write_text(json.dumps(bounds,separators=(',',':'))+'\n')
    print(out['status'],'FF',len(bounds),'impossible',len(bad),'max',out['max_unconstrained_minimax_um'],flush=True)
    for x in out['highest_bounds'][:12]:print(x['FF'],x['unconstrained_optimistic_minimax_um'],len(x['constraints']),flush=True)


if __name__=='__main__':main()
