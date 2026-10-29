"""Exact allocator-input identity for safe reuse of one partition's FF sites."""
import hashlib,json

def identity(plan, part):
    import schema as S
    from gen_phys import type_pins
    m=S.Plan(plan);t=m.ptype(part);slots=[]
    for slot in t.get('ft_slots',[]):
        slots.append({k:slot[k] for k in ('name','width','stations','in_face','out_face')})
    phy=[];A=m.rect(part)
    for dom in plan['die'].get('pg',{}).get('domains',[]):
        r=dom.get('rect_um')
        if not r:continue
        x0,y0,x1,y1=max(A[0],r[0]),max(A[1],r[1]),min(A[2],r[2]),min(A[3],r[3])
        if x1>x0 and y1>y0:phy.append(sorted([m.to_type(part,(x0,y0)),m.to_type(part,(x1,y1))]))
    payload=dict(outline=t['outline_um'],pins=type_pins(m,m.parts[part]['type']),
                 hard_cores=t.get('hard_cores',[]),contents=t.get('contents',[]),slots=slots,
                 clock=t.get('clock',{}),reset=t.get('reset',{}),channels=t.get('channels',[]),
                 internal_stations=t.get('internal_stations',[]),phy=phy,
                 signal_policy=plan['die'].get('layer_budget'),pg=plan['die'].get('pg',{}).get('grid'))
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
