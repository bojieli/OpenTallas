import sys,json
sys.path.insert(0,'tools/die_plan')
import schema as S, reset_tree as R
from placement_obstacles import placement_boxes
P=S.Plan(S.load('physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json'))
raw=P.raw
tot=0;bad=0;rows=[]
def lefold(t,clear=R.CLEAR_UM):
    out=[]
    for c in list(t.get("hard_cores", []) or []) + [c for c in t.get("contents", []) or [] if c.get("lef")]:
        if "origin_um" not in c or "outline_um" not in c: continue
        (ox, oy), (cw, ch) = c["origin_um"], c["outline_um"]
        if c.get("orient") in ("R90", "R270", "MXR90", "MYR90"): cw, ch = ch, cw
        out.append((ox - clear, oy - clear, ox + cw + clear, oy + ch + clear))
    return out
for tn,t in raw['partition_types'].items():
    ct=((t.get('clock') or {}).get('landing_contract') or {}).get('collector_tree')
    if not ct or 'relays' not in ct or t.get('hard'): continue
    tt=P.types[tn]
    new=list(placement_boxes(tt,halo=R.CLEAR_UM).values()); old=lefold(tt)
    inside=lambda p,B,c=0:[b for b in B if b[0]+c<p[0]<b[2]-c and b[1]+c<p[1]<b[3]-c]
    nb=0;ex=[]
    for r in ct['relays']:
        tot+=1
        if inside(r["xy"],new,R.CLEAR_UM-0.001):
            nb+=1; ex.append((r['q'],r['xy'],[round(v,3) for v in inside(r['xy'],new)[0]]))
    bad+=nb
    rows.append((tn,len(ct['relays']),len(old),len(new),nb,ex[:2]))
for r in rows:
    if r[4] or r[2]!=r[3]: print(r)
print('TOTAL relays',tot,'newly-blocked',bad)
