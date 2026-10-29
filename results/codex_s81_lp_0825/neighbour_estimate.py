#!/usr/bin/env python3
"""Price the immediate neighbour FT consequence of the LP window proposal.

Only reports a candidate. It does not change the frozen die or lane latencies.
For same-order endpoint windows, the first/last-bit Manhattan bound determines
how many <=405-um segments the existing feedthrough needs after one face moves.
"""
import json,math
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent
p=json.loads((R/'physical/die_plan/s81/die_plan.json').read_text())
fit=json.loads((R/'results/s81_lp_3_1029/parent_estimate_T.json').read_text())
parts={x['name']:x for x in p['partitions']}
def world_window(part,face,window):
    q=parts[part];w,h=p['partition_types'][q['type']]['outline_um'];ori=q['orient']
    reflect=(face in ('N','S') and ori in ('MY','R180')) or (face in ('W','E') and ori in ('MX','R180'))
    span=w if face in ('N','S') else h;off=q['origin_um'][0 if face in ('N','S') else 1]
    return [off+span-window[1],off+span-window[0]] if reflect else [off+window[0],off+window[1]]
def local_window(part,face,window):
    q=parts[part];w,h=p['partition_types'][q['type']]['outline_um'];ori=q['orient']
    reflect=(face in ('N','S') and ori in ('MY','R180')) or (face in ('W','E') and ori in ('MX','R180'))
    span=w if face in ('N','S') else h;off=q['origin_um'][0 if face in ('N','S') else 1]
    return [span-(window[1]-off),span-(window[0]-off)] if reflect else [window[0]-off,window[1]-off]
def point(face,x,w,h):return {'N':(x,h),'S':(x,0),'E':(w,x),'W':(0,x)}[face]
def length(ft,w,h):
    pairs=zip(ft['in_window_um'],ft['out_window_um'])
    return max(sum(abs(a-b) for a,b in zip(point(ft['in_face'],i,w,h),point(ft['out_face'],o,w,h))) for i,o in pairs)
rows=[]
for inst,f in fit.items():
    t=p['partition_types'][f['type']];face=f['link_face'];moves=f['proposed']['moved_coll_windows']|f['proposed']['moved_street_windows']
    bus_moves={k:v for k,v in moves.items() if any(b['name']==k for b in t['buses'])}
    for ft in t['ft_slots']:
        if ft['name'] in moves:
            for end in ('in','out'):
                if ft[end+'_face']==face:bus_moves[ft['name']+('_i' if end=='in' else '_o')]=moves[ft['name']]
    for port in p['ports']:
        for end,other in (('src','dst'),('dst','src')):
            e=port[end];z=port[other]
            if e['part']!=inst or e['bus'] not in bus_moves or z['part']=='@die':continue
            world=world_window(inst,face,bus_moves[e['bus']]);qt=p['partition_types'][parts[z['part']]['type']]
            if not z['bus'].endswith(('_i','_o')):continue
            ft=next((s for s in qt.get('ft_slots',[]) if s['name']==z['bus'][:-2]),None)
            if ft is None:continue
            which='in' if z['bus'].endswith('_i') else 'out'
            new=json.loads(json.dumps(ft));new[which+'_window_um']=local_window(z['part'],ft[which+'_face'],world)
            w,h=qt['outline_um'];old_len=length(ft,w,h);new_len=length(new,w,h)
            old_k=ft['stations'];new_k=max(old_k,math.ceil(new_len/405))
            rows.append(dict(parent=inst,port=port['id'],parent_bus=e['bus'],neighbour=z['part'],
                             neighbour_type=parts[z['part']]['type'],slot=ft['name'],end=which,
                             new_world_window_um=world,new_type_window_um=new[which+'_window_um'],
                             old_max_bit_manhattan_um=round(old_len,3),new_max_bit_manhattan_um=round(new_len,3),
                             old_stations=old_k,estimated_stations=new_k,estimated_added_cycles=new_k-old_k))
out=dict(verdict='ESTIMATE ONLY; same-order first/last bits, actual full-plan bind/reach required',
         changed_endpoints=len(rows),estimated_extra_station_cycles=sum(r['estimated_added_cycles'] for r in rows),
         rows=rows)
(O/'neighbour_estimate.json').write_text(json.dumps(out,indent=1)+'\n')
print(out['changed_endpoints'],out['estimated_extra_station_cycles'])
