#!/usr/bin/env python3
"""KV-PLAN 10-25 mouth capacity: per abutted boundary segment: pins crossing, common channel-mouth length (both sides' core-free intervals, +-4 um
clearance; hard cores projected on the face axis = straight-through channel).  usage: mouth_capacity.py PLAN [CENTRE 0|1] [--json OUT]"""
import sys,collections,json
sys.path.insert(0,'/home/ubuntu/wt/kv-plan-1025r/tools/die_plan')
import schema as S
from pathlib import Path
J=sys.argv[1] if len(sys.argv)>1 else '/home/ubuntu/wt/kv-plan-1025r/physical/die_plan/qwen_kvsys/die_plan.json'
P=S.Plan(S.load(J),Path(J).resolve())
CL=4.0
CENTRE=int(sys.argv[2]) if len(sys.argv)>2 and sys.argv[2].isdigit() else 0
JOUT=sys.argv[sys.argv.index('--json')+1] if '--json' in sys.argv else None
def die_cores(inst):
    t=P.ptype(inst); out=[]
    cs=[c for c in t.get('hard_cores',[]) if 'origin_um' in c]
    dx=dy=0.0
    if CENTRE and cs:
        W,H=t['outline_um']
        mnx=min(c['origin_um'][0] for c in cs); mxx=max(c['origin_um'][0]+c['outline_um'][0] for c in cs)
        mny=min(c['origin_um'][1] for c in cs); mxy=max(c['origin_um'][1]+c['outline_um'][1] for c in cs)
        dx=((W-mxx)-mnx)/2; dy=((H-mxy)-mny)/2 if CENTRE>1 else 0.0
    for c in cs:
        x0,y0=c['origin_um']; w,h=c['outline_um']; x0+=dx; y0+=dy
        a=P.to_die(inst,(x0,y0)); b=P.to_die(inst,(x0+w,y0+h))
        out.append((min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])))
    return out
def blocked(inst, face, lo, hi):
    """along-face intervals blocked by inst's cores (projected), clipped to [lo,hi]"""
    iv=[]
    for x0,y0,x1,y1 in die_cores(inst):
        a,b=((y0,y1) if face in 'EW' else (x0,x1))
        iv.append((max(lo,a-CL),min(hi,b+CL)))
    return [v for v in iv if v[1]>v[0]]
def free_len(lo,hi,iv):
    iv=sorted(iv); cur=lo; tot=0
    for a,b in iv:
        if a>cur: tot+=a-cur
        cur=max(cur,b)
    return tot+max(0,hi-cur)
seg=collections.defaultdict(lambda: dict(pins=0,ports=0))
for pid,pr in P.ports.items():
    s,d=pr['src']['part'],pr['dst']['part']
    if s not in P.parts or d not in P.parts: continue
    key=(s,d,pr['face']) if s<d else (d,s,S.OPP[pr['face']])
    seg[key]['pins']+=pr['width']; seg[key]['ports']+=1
    seg[key].setdefault('win',[]).append(tuple(pr['window_um']))
rows=[]
for (a,b,f),v in seg.items():
    ra,rb=P.rect(a),P.rect(b)
    if f in 'EW': lo,hi=max(ra[1],rb[1]),min(ra[3],rb[3])
    else: lo,hi=max(ra[0],rb[0]),min(ra[2],rb[2])
    if hi<=lo: continue
    fa=free_len(lo,hi,blocked(a,f,lo,hi)+blocked(b,S.OPP[f],lo,hi))
    rows.append((v['pins']/max(fa,1e-3),a,b,f,v['pins'],round(hi-lo,1),round(fa,1),P.parts[a]['type'],P.parts[b]['type']))
rows.sort(reverse=True)
print('segments',len(rows),'over 16/um',sum(r[0]>16 for r in rows),'over 12/um',sum(r[0]>12 for r in rows),'over 8/um',sum(r[0]>8 for r in rows))
for r in rows[:25]: print('%6.1f/um %s|%s %s pins %d seg %s mouth %s  %s|%s'%r)
if JOUT:
    json.dump(dict(schema='opentallas.kv_mouth_capacity.v1', plan=J, clearance_um=CL, centre=CENTRE,
                   rows=[dict(pins_per_um=round(r[0],2), a=r[1], b=r[2], face=r[3], pins=r[4], seg_um=r[5], mouth_um=r[6],
                              type_a=r[7], type_b=r[8]) for r in rows]), open(JOUT,'w'), indent=1)
