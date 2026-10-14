#!/usr/bin/env python3
"""Assign native r3 head subslots inside v1.1, using conservative pin-region Manhattan bounds.
83 roots: 3 shared leaves and 16 copies of stin, stk, nb1, nb2 and lane.
New leaves require their assigned regions and physical qualification; closed lane/ktree views stand.
"""
import argparse
import itertools
import json
import math
from pathlib import Path

W,H=1079.976,492.456 # actual exported v1.1 outline; nominal 1080 x 492.48
CLEAR=5.4
SHAPES={'front':(648.,32.4),'ktree':(151.2,97.2),'score':(43.2,43.2),
        'lane':(129.6,129.6),'stin':(32.4,43.2),'stk':(32.4,21.6),'nb':(32.4,10.8)}

def overlap(a,b):
    return not (a[0]+a[2]+CLEAR<=b[0]+1e-6 or b[0]+b[2]+CLEAR<=a[0]+1e-6
                or a[1]+a[3]+CLEAR<=b[1]+1e-6 or b[1]+b[3]+CLEAR<=a[1]+1e-6)

def face(r,f):
    x,y,w,h=r
    return {'N':[(x,y+h),(x+w,y+h)],'S':[(x,y),(x+w,y)],
            'W':[(x,y),(x,y+h)],'E':[(x+w,y),(x+w,y+h)]}[f]

def bound(a,b):
    return max(abs(x-u)+abs(y-v) for (x,y),(u,v) in itertools.product(a,b))

def centre(pts):return tuple(sum(p[k] for p in pts)/len(pts) for k in range(2))

def candidates(shape,fixed):
    w,h=shape
    for ix in range(1,int((W-w-CLEAR)/CLEAR)+1):
        x=round(ix*CLEAR,6)
        for iy in range(1,int((H-h-CLEAR)/CLEAR)+1):
            r=(x,round(iy*CLEAR,6),w,h)
            if not any(overlap(r,f) for f in fixed):yield r

def plan():
    front=(216.,5.4,*SHAPES['front']);kt=(388.8,54.,*SHAPES['ktree']);score=(550.8,54.,*SHAPES['score'])
    grid=[(43.2+172.8*c,54.+151.2*r,*SHAPES['lane']) for c in range(6) for r in range(3)
          if not (r==0 and c in (2,3))]
    lanes={15-i:r for i,r in enumerate(grid)}
    placed=[front,kt,score]+list(lanes.values())
    free={k:list(candidates(SHAPES[k],placed)) for k in ['stin','stk','nb']}
    rows=[];children={'front':front,'ktree':kt,'score':score};hops=[]
    # Ports are assigned by physical lane order across the front's north face.
    front_order=sorted(lanes,key=lambda t:(lanes[t][0],lanes[t][1]))
    fronts={t:[(front[0]+front[2]*j/16,front[1]+front[3]),
               (front[0]+front[2]*(j+1)/16,front[1]+front[3])]
            for j,t in enumerate(front_order)}
    # Place the farthest lanes first; every pin in each region is bounded.
    for t in sorted(lanes,key=lambda t:-lanes[t][1]):
        lane=lanes[t];x,y=lane[:2]
        li=[(x+0.7,y),(x+24.,y)];lo=[(x+129.6,y+48.),(x+129.6,y+93.)]
        choices=[]
        for r in free['stin']:
            if any(overlap(r,f) for f in placed):continue
            a=bound(fronts[t],face(r,'E'));b=bound(face(r,'S'),li)
            choices.append((max(a,b),a+b,r,a,b))
        if not choices:raise ValueError('no stin placement')
        _,_,sin,a,b=min(choices);placed.append(sin);children[f'stin{t}']=sin
        hops.extend([(f'front->stin{t}',a),(f'stin{t}->lane{t}',b)])
        # The closed ktree north-face group for this unchanged logical lane index.
        kp_x=kt[0]+101.34-96.0*t/15
        kp=[(kp_x-3.2,kt[1]+97.2),(kp_x+3.2,kt[1]+97.2)]
        choices=[]
        for r in free['stk']:
            if any(overlap(r,f) for f in placed):continue
            a=bound(lo,face(r,'N'));b=bound(face(r,'S'),kp)
            choices.append((max(a,b),a+b,r,a,b))
        if not choices:raise ValueError('no stk placement')
        _,_,stk,a,b=min(choices);placed.append(stk);children[f'stk{t}']=stk
        hops.extend([(f'lane{t}->stk{t}',a),(f'stk{t}->ktree',b)])
        # v1.1 assigned nb E-face region: 197.100..295.308 at 0.096 um/bit.
        target=[(W,197.1+0.096*64*t),(W,197.1+0.096*(64*t+63))]
        lc=centre(lo);tc=centre(target)
        ideal1=tuple(lc[k]+(tc[k]-lc[k])/3 for k in range(2))
        ideal2=tuple(lc[k]+2*(tc[k]-lc[k])/3 for k in range(2))
        available=[r for r in free['nb'] if not any(overlap(r,f) for f in placed)]
        c1=[r for r in available if bound(lo,face(r,'W'))<=500]
        c2=[r for r in available if bound(face(r,'E'),target)<=500]
        dist=lambda r,p:abs(r[0]+r[2]/2-p[0])+abs(r[1]+r[3]/2-p[1])
        c1=sorted(c1,key=lambda r:dist(r,ideal1))[:100]
        c2=sorted(c2,key=lambda r:dist(r,ideal2))[:100]
        best=None
        for r1 in c1:
            a=bound(lo,face(r1,'W'))
            for r2 in c2:
                if overlap(r1,r2):continue
                b=bound(face(r1,'E'),face(r2,'W'));c=bound(face(r2,'E'),target)
                trial=(max(a,b,c),a+b+c,r1,r2,a,b,c)
                if best is None or trial<best:best=trial
        if best is None:raise ValueError('no NB pair placement')
        _,_,n1,n2,a,b,c=best;placed.extend([n1,n2]);children[f'nb1_{t}']=n1;children[f'nb2_{t}']=n2
        hops.extend([(f'lane{t}->nb1_{t}',a),(f'nb1_{t}->nb2_{t}',b),(f'nb2_{t}->die_nb',c)])
        children[f'lane{t}']=lane
        rows.append(dict(lane=t,lane_xy_um=list(lane[:2]),stin=list(sin),stk=list(stk),nb1=list(n1),nb2=list(n2)))
    # Keep every parent data pin fixed. Front inputs use identical x coordinates
    # on its S face, so the bound is bit matched rather than cross-bus diameter.
    parent_inputs={'ti':[224.508,673.212], 'e':[686.076,687.516]}
    for name,span in parent_inputs.items():
        assert front[0]<=span[0]<=span[1]<=front[0]+front[2]
        hops.append((f'die_{name}->front (bit matched)',front[1]))
    score_target=[(706.092,0.),(709.26,0.)]
    # pack_fault is an independent scalar connection, not part of f_t.
    pack_pin=[(550.8,front[1]+front[3])]
    hops.extend([('ktree->score',bound(face(kt,'E'),face(score,'W'))),
                 ('front.pack_fault->score',bound(pack_pin,face(score,'N'))),
                 ('score->die_s',bound(face(score,'S'),score_target)),
                 ('score.kt_rst_n->ktree',bound(face(score,'W'),face(kt,'E')))])
    ov=[(a,b) for a,b in itertools.combinations(children,2) if overlap(children[a],children[b])]
    outside=[n for n,r in children.items() if r[0]<0 or r[1]<0 or r[0]+r[2]>W+1e-6 or r[1]+r[3]>H+1e-6]
    clocks=[dict(child=n,rtl_clock=('ck_'+n if n in ['front','score'] else 'ck_kt' if n=='ktree' else
             f"ck_{'nb1' if n.startswith('nb1_') else 'nb2' if n.startswith('nb2_') else ''.join(c for c in n if not c.isdigit())}[{n.split('_')[-1] if '_' in n else ''.join(c for c in n if c.isdigit())}]"),
             child_clock_pin='clk',clock_pin_assignment='actual leaf pin required at hardening') for n in children]
    assert len(children)==len(clocks)==83
    worst=max(hops,key=lambda h:h[1]);valid=not ov and not outside and worst[1]<=500
    return dict(schema='qwen-kvsys-head-native-plan/r3',slot='qkd_rhead',contract='kvsys_v1.1',
        slot_outline_um=[W,H],canonical_orientation='R0; control face S',clock_entries_per_head=83,
        rtl_master='ot_qkh_head_native_r3',latency_change_cycles=0,
        reach_method='maximum Manhattan distance between every endpoint of the assigned pin regions',
        reach_rule_um=500,valid=valid,worst_hop=dict(name=worst[0],um=round(worst[1],3)),
        overlaps=ov,outside=outside,front_port_order_W_to_E=front_order,
        shared_children={n:list(children[n]) for n in ['front','ktree','score']},lanes=sorted(rows,key=lambda r:r['lane']),
        children={n:list(r) for n,r in children.items()},clock_entries=clocks,
        parent_data_pin_assignments=dict(front_S_bit_matched=parent_inputs,
            front_pack_fault_N=list(pack_pin[0]),score_output_S=list(score_target)),
        reset_rule='preserve the RTL reset topology; assign the external asynchronous reset distribution '
                   'and measure recovery/removal and native reset paths before physical qualification',
        hops=[dict(name=n,um=round(d,3)) for n,d in hops],
        qualification='geometry assignment proposal; fresh leaf physical views, actual clock pins and native pair reach required')

def main():
    a=argparse.ArgumentParser();a.add_argument('out',type=Path);args=a.parse_args();r=plan()
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['valid','clock_entries_per_head','worst_hop','overlaps','outside']}))
    return 0 if r['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
