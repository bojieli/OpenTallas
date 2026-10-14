#!/usr/bin/env python3
"""Compare baseline and experimental head pin geometry without allocating relays.

python tools/qwen_tp8/ectl_multicast_candidate_probe.py OUT [--candidate]
Candidate remains unclosed. This does not submit a route or alter any gate.
"""
import json
import os
from pathlib import Path
import sys
from collections import Counter
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import die_top_lint as D

if '--timing' in sys.argv:
    os.environ['OT_PAIR_TIMING'] = str(Path(sys.argv[sys.argv.index('--timing') + 1]).resolve())
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
if '--candidate' in sys.argv:
    os.environ['OT_TP8_ECTL_PIN_REPLAN_CANDIDATE'] = '1'
else:
    os.environ.pop('OT_TP8_ECTL_PIN_REPLAN_CANDIDATE', None)
D.QWEN_RECIPE = 'tp8b'
D.QWEN_RECIPES['tp8b'] = dict(D.QWEN_TP8B, relay_pitch=0)
v, model, G = D.load_qwen()
M = v.masters(model, 1)
pos = G._pin_pos(v, model)
sys.path.insert(0, str(ROOT/'tools/hier_contract'))
from pair_check import Gate
by={i.name:i for i in model['insts']}
import re
clock_net={(i,p.lstrip('*')):re.sub(r'_r\d+$','',b) for b,c,n,es in model['buses'] if c=='clock_trunk' for i,p in es}
gate=Gate(default_um=500.0,buses=model['buses'],clock_net=clock_net)
rows=[]
unicast=[]
for bid, cls, bits, ends in model['buses']:
    if bid.startswith('tp_') and len(ends) == 3:
        points=[pos(*e) for e in ends]
        span=max(x for x,y in points)-min(x for x,y in points)+max(y for x,y in points)-min(y for x,y in points)
        pairs=[abs(points[0][0]-x)+abs(points[0][1]-y) for x,y in points[1:]]
        src,sp=ends[0]
        limits=[gate.limit(src,by[src].master,sp,dst,by[dst].master,dp) for dst,dp in ends[1:]]
        rows.append(dict(pair_limits_um=limits,pair_over=sum(d>lim for d,lim in zip(pairs,limits)),bus=bid,bits=bits,endpoints=ends,points_um=points,span_um=round(span,4),
                         source_pair_um=[round(d,4) for d in pairs],over_500=span>500))
    elif bid.startswith(('te_','ts_')) and len(ends)==2:
        src,sp=ends[0];dst,dp=ends[1];a,b=pos(*ends[0]),pos(*ends[1])
        length=abs(a[0]-b[0])+abs(a[1]-b[1])
        limit=gate.limit(src,by[src].master,sp,dst,by[dst].master,dp)
        unicast.append(dict(bus=bid,endpoints=ends,points_um=[a,b],length_um=length,pair_limit_um=limit,pair_over=length>limit))
q=M['qkd_rhead'];pw=v.port_widths(model,1)
pins=v.pin_rects(q,1,{p:pw.get((q.name,p),0) for p in q.order})
# Every signal rectangle of this master must avoid another signal on its layer.
collisions=[]
for j,(name,layer,rect) in enumerate(pins):
    for name2,layer2,rect2 in pins[j+1:]:
        if layer != layer2:continue
        if min(rect[2],rect2[2]) > max(rect[0],rect2[0])+1e-7 and min(rect[3],rect2[3]) > max(rect[1],rect2[1])+1e-7:
            collisions.append([name,name2,layer])
lattice_off=[]
for name,layer,rect in pins:
    if layer == 'M5':
        x=(rect[0]+rect[2])/2
        err=abs((x-0.012)/0.048-round((x-0.012)/0.048))*0.048
        if err>1e-6:lattice_off.append([name,err])
clocks=[(name,layer,rect) for name,layer,rect in pins if name.split('[')[0]=='ck']
source_clocks=[]
for i in model['insts']:
    if i.master.startswith('qkd_ectl_'):
        sp=M[i.master].ports['ck']
        source_clocks.append(dict(instance=i.name,master=i.master,orientation=i.orient,master_pin_spec=list(sp),die_point=pos(i.name,'ck')))
report=dict(source_clock_pins=source_clocks,head_orientations=dict(Counter(i.orient for i in model['insts'] if i.master=='qkd_rhead')),
            head_m5_local_lattice_errors=lattice_off,schema='opentallas.tp8.ectl-pin-candidate.v1', candidate='--candidate' in sys.argv,
            summary=dict(multicast_buses=len(rows),over_500=sum(q['over_500'] for q in rows),
                         max_span_um=max(q['span_um'] for q in rows),max_source_pair_um=max(max(q['source_pair_um']) for q in rows),
                         signal_pin_rectangle_collisions=len(collisions),pair_table_masters=len(gate.t),
                         multicast_pairs_over=sum(q['pair_over'] for q in rows),
                         e_s_pairs_over=sum(q['pair_over'] for q in unicast),head_m5_local_lattice_errors=len(lattice_off)),
            head_outline=[q.w,q.h],head_clock=clocks,rows=rows,e_s_unicast=unicast,pin_collisions=collisions[:100],
            pin_plan=model['tp8b_v5'].get('ectl_pin_replan_candidate'),
            scope='Geometry only; unclosed head parent owes actual pin-register placement, clock tree, fanout timing and full die cut/route/STA proof')
(out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
# Sparse candidate pin assignment including per-bit positions for native ti bit mapping.
(out/'head_pin_rects.json').write_text(json.dumps(pins,indent=1)+'\n')
print(json.dumps(report['summary']))
