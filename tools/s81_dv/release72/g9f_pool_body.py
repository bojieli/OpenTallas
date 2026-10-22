#!/usr/bin/env python3
"""Reserve the mapped raw pool area without shrinking its neighboring corridor.
This is a pool-only minimum; CN/IK extra logic and repaired pool remain open.
"""
import json,sys,math
from pathlib import Path

def reserve(plan):
    bs={b['name']:b for b in plan['blocks']};n,s=bs['s_3N'],bs['s_3S']
    area=95849.838540;delta=43.2*math.ceil((area/.4/n['w'])/43.2)
    assert abs(delta-216)<1e-6,(delta,n)
    before={k:{f:bs[k][f] for f in ['x','y','w','h']} for k in ['s_3N','s_3S']}
    oldtop=n['y']+n['h'];gap=s['y']-oldtop
    n['h']+=delta;s['y']+=delta
    moved={i:b['name'] for i,b in enumerate(plan['blocks']) if b['name'] in before}
    for l in plan['links']:
        for end in l['e']:
            name=moved.get(end[0])
            if name=='s_3S' or name=='s_3N' and abs(end[3]-oldtop)<.01:
                end[3]=round(end[3]+delta,4)
        for key in ['h','sp','s','L','station_dirs']:l.pop(key,None)
    W,H=plan['facts']['die_um'];errors=[]
    for name in before:
        b=bs[name]
        if b['x']<0 or b['y']<0 or b['x']+b['w']>W or b['y']+b['h']>H:errors.append(name+' out of reticle')
        for q in plan['blocks']+plan.get('blockages',[]):
            if q is b:continue
            if b['x']<q['x']+q['w'] and b['x']+b['w']>q['x'] and b['y']<q['y']+q['h'] and b['y']+b['h']>q['y']:errors.append([name,q.get('name','blockage')])
    assert not errors,errors
    assert abs(s['y']-(n['y']+n['h'])-gap)<1e-6
    record=dict(source_pool='75c077ec9 original mapped source; native FAIL retained',mapped_area_um2=area,
      area_unit_factor=1,unit_authority='ASAP7 liberty AND2x2 area0.08748 = LEF0.324x0.270um; measured by RTL gap owner',
      utilization_range=[.4,.6],outline_range_um2=[area/.6,area/.4],added_height_um=delta,
      added_outline_um2=delta*n['w'],preserved_corridor_um=gap,before=before,
      after={k:{f:bs[k][f] for f in ['x','y','w','h']} for k in before},
      all_changed_bodies_nonoverlapping=True,qualification='POOL-ONLY RESERVATION; extra CN/IK and repaired-pool mapped area, native, placement and clock remain OPEN')
    plan['facts']['pool_body_growth']=record
    return record
if __name__=='__main__':
    p=json.load(open(sys.argv[1]));r=reserve(p);Path(sys.argv[2]).write_text(json.dumps(p,indent=1)+'\n');print(json.dumps(r,indent=1))
