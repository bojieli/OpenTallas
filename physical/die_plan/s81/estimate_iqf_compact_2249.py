#!/usr/bin/env python3
"""Read-only IQF NE-anchored locality estimate; never route/adopt this draft."""
import argparse
import json
import math
from pathlib import Path

a=argparse.ArgumentParser();a.add_argument('plan');a.add_argument('out');x=a.parse_args()
p=json.load(open(x.plan));parts={q['name']:q for q in p['partitions']};q=parts['iqf'];t=p['partition_types'][q['type']]
assert q.get('orient','R0')=='R0' and all(b['face']in'NE' for b in t['buses'])
assert all(f[e+'_face']in'NE' for f in t['ft_slots']for e in('in','out'))
W,H=406.08,259.2;ox,oy=q['origin_um'];ow,oh=t['outline_um'];nx,ny=round(ox+ow-W,6),round(oy+oh-H,6)
assert all(abs(v/8.64-round(v/8.64))<1e-8 for v in(nx,ny,W,H))
buses={b['name']:b for b in t['buses']};slots={f['name']:f for f in t['ft_slots']}
def width(n):return buses[n]['width'] if n in buses else slots[n[:-2]]['width']
order={'N':['ft1_i','ft0_o','flt_o0','idx_i0','idx_o0','ql_i0','qc_o0'], 'E':['ft1_o','ft0_i']}
windows={}
for face,names in order.items():
    at=4.32
    for name in names:
        # Reserve one epoch bit conservatively and half the pins per layer.
        span=math.ceil(math.ceil((width(name)+1)/2)/5.5/.192)*.192
        windows[name]=dict(face=face,window_um=[round(at,6),round(at+span,6)],
                           layers=['M7','M5']if face=='N'else['M6','M4'],order='lsb_low',width=width(name))
        at+=span+.432
    assert at<({'N':W,'E':H}[face]-4.32), (face,at)
adj=[]
for pr in p['ports']:
    side=next((s for s in('src','dst')if pr[s]['part']=='iqf'),None)
    if side is None:continue
    bus=pr[side]['bus'];g=windows[bus];other=pr['dst'if side=='src'else'src']
    win=[(nx if g['face']=='N'else ny)+v for v in g['window_um']]
    adj.append(dict(port=pr['id'],iqf_bus=bus,neighbour=other,world_window_um=win,
                    unchanged_abutment_line=oy+oh if g['face']=='N'else ox+ow))
kv=[]
for z in p['partitions']:
    if z['type']=='ot_s81sl_kv_leaf__t2':
        w,h=p['partition_types'][z['type']]['outline_um'];xx,yy=z['origin_um']
        kv.append(dict(part=z['name'],box_um=[xx,yy,xx+w,yy+h],adjacent_to_iqf=False,
                       minimum_y_gap_um=round(yy-(oy+oh),6)))
out=dict(verdict='ANALYTIC CANDIDATE ONLY; no plan adoption/P&R',source_plan=x.plan,
         old_box_um=[ox,oy,ox+ow,oy+oh],new_box_um=[nx,ny,nx+W,ny+H],outline_um=[W,H],
         anchor='old NE corner; N/E abutment lines unchanged; no W/S functional signals',
         lattice_note='403.2um width requires an off-grid origin; round up to406.08=47x8.64um',
         std_area_um2=19865.25,fill=19865.25/(W*H),
         per_layer_pins=dict(N_M7=2159,N_M5=2145,E_M6=1246,E_M4=1244,E_M7=2),
         per_layer_density=dict(N_M7=2159/W,N_M5=2145/W,E_M6=1246/H,E_M4=1244/H,E_M7=2/H),
         regular_windows=windows,immediate_endpoint_draft=adj,
         freed_channel_rects_um=[[ox,oy,nx,oy+oh],[nx,oy,ox+ow,ny]],
         kv_leaf_t2_adjacency=kv,rtl_or_cycle_changes=0,
         pending=['author-approved application of local partition outline event','couple neighbour bus/FT endpoints',
                  'recompute FT reach/station counts and every resulting lane-cycle change',
                  'reset/START/clock/landing contract recomposition; no new ft0_i ring assumed',
                  'G0C/bind/die clock and actual placement review before route'])
Path(x.out).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(outline=out['outline_um'],fill=out['fill'],ports=len(adj),kv_adjacency=False)))
