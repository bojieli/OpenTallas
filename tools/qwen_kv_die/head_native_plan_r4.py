#!/usr/bin/env python3
"""Assign native r3 head subslots inside v1.1, using conservative pin-region Manhattan bounds.
86 roots: four front quarters, ktree/score and and 16 copies of stin, stk, nb1, nb2 and lane.
New leaves require their assigned regions and physical qualification; closed lane/ktree views stand.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

W,H=1079.976,492.456 # actual exported v1.1 outline; nominal 1080 x 492.48
REACH=500  # KVPLAN2 2026-10-16: --reach (die planning margin 400 = 0.9 x measured KV reach 446)
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

def read_pins(path):
    pins={};pin=None
    with Path(path).open() as f:
        for line in f:
            t=line.split()
            if t[:1]==['PIN']:pin=t[1]
            elif pin and t[:1]==['RECT'] and pin not in pins:
                x0,y0,x1,y1=map(float,t[1:5]);pins[pin]=((x0+x1)/2,(y0+y1)/2)
            elif t[:1]==['END'] and len(t)>1 and t[1]==pin:pin=None
    return pins


def region(points):
    x0=min(x for x,y in points);x1=max(x for x,y in points)
    y0=min(y for x,y in points);y1=max(y for x,y in points)
    return [(x0,y0),(x1,y0),(x0,y1),(x1,y1)]


# KV-BIND12 10-20 (OT_KV_QKH_SAFE32 heads, default off): the strict-bind successors ot_qkh_lane8_nc32c (172.8 x 172.8)
# and ot_qkh_ktree_lk_nc32c (172.8 x 129.6) close the 43.2 / 21.6 gaps of the v1.1 grid.  --safe32 re-plans the static
# (ASTK_ST) head -- 4 fronts, ktree, score4 and 16 x (stin, stk, lane), no nb relays -- on a wider grid read from the real
# nc32c LEF sizes and pins: SAFE32 below (column pitch = lane + 43.2 gap for the stin / stk column, lattice x).
# 6 x 3 lane slots (172.8 + 43.2 gap columns from x 43.2, rows from y 54 at 183.6 = 10.8-um row gaps); the ktree in row 1 at
# x 658.8 (frees one slot), score4 in the row-0 slot under it (pack_fault / kt_rst_n / die s all short); the fronts move with
# the centred control tile (front_dx = (1339.2 - 1080) / 2).  Outlines on the 43.2 lattice: r4 594 -> 604.8, ft (rows >= 1
# up 21.6 for the 21.6-um T1 / S2 zone) 615.6 -> 648.  Reach: 2-hop chains of 16 lanes this size cannot all stay <= 400 in
# any 6 x 3 (ideal-station bound 422); 5 x 4 (alt_5x4) meets ~400 but each head grows ~300 um in y (x 32 heads of die height).
SAFE32 = dict(cols=6, rows=3, x0=43.2, col_pitch=216.0, y0=54.0, row_pitch=183.6, ktree_cell=(1, 3), ktree_xy=(658.8, 237.6),
              front_dx=129.6, score=(604.8, 54.0), outline=(1339.2, 604.8), outline_ft=(1339.2, 648.0), channel_dy=21.6)
SAFE32_VIEWS = {'lane': ('ot_qkh_lane8_nc32c', 'ot_qkh_lane8_nc32c'), 'ktree': ('ot_qkh_ktree_lk_nc32c', 'ot_qkh_ktree_lk_nc32c'),
                'score': ('qkh_r4_score4_1014', 'ot_qkh_head_score4_native')}


def safe32_geo(root, ft=False, cfg=None):
    """the safe32 grid (lane slots, ktree, score, fronts) from the nc32c LEF sizes; ft: rows >= 1 move up channel_dy"""
    c = dict(SAFE32, **(cfg or {}))
    size = {}
    for k, (kit, cell) in SAFE32_VIEWS.items():
        for line in (Path(root) / 'physical/ref_tile' / kit / 'views' / cell / f'{cell}.lef').open():
            t = line.split()
            if t[:1] == ['SIZE']:
                size[k] = (float(t[1]), float(t[3]))
                break
    lw, lh = size['lane']
    dy = c['channel_dy'] if ft else 0.
    def cell(r, k):
        return (round(c['x0'] + c['col_pitch'] * k, 6), round(c['y0'] + c['row_pitch'] * r + (dy if r >= 1 else 0.), 6))
    kr, kc = c['ktree_cell']
    kt = cell(kr, kc)
    grid = [cell(r, k) for r in range(c['rows']) for k in range(c['cols']) if (r, k) != (kr, kc)]
    # score4 (43.2^2): in the front band W of front0 unless placed explicitly (fronts at 216 + front_dx + 135 g)
    sc = tuple(c['score']) if c['score'] else (round(216. + c['front_dx'] - 43.2 - 43.2, 6), 5.4)
    grid = [g for g in grid if not overlap((*g, lw, lh), (*sc, *size['score']))]      # a lane slot the score takes
    if c.get('ktree_xy'):         # the ktree off the cell lattice (still on the 43.2-um x lattice): free the slots it covers
        kt = tuple(c['ktree_xy'])
        if kt[1] >= c['y0'] + c['row_pitch'] - 1e-6:          # a ktree in lane row >= 1 moves with those rows (ft channel)
            kt = (kt[0], round(kt[1] + dy, 6))
        grid = [cell(r, k) for r in range(c['rows']) for k in range(c['cols'])]
        grid = [g for g in grid if not overlap((*g, lw, lh), (*kt, *size['ktree'])) and not overlap((*g, lw, lh), (*sc, *size['score']))]
    W_, H_ = c['outline_ft'] if ft else c['outline']
    return dict(W=W_, H=H_, grid=grid, kt=kt, score=sc, front_dx=c['front_dx'], channel_dy=dy, views=SAFE32_VIEWS,
                shapes=dict(SHAPES, lane=size['lane'], ktree=size['ktree'], score=size['score']), nb=False, cfg=c)


def plan(closed_pins=None, channel=None, perm=None, kt_x=388.8, score_x=550.8, safe32=None):
    """channel (kvsys v1.4.3 near-head feed-through, KV die lead 2026-10-15): (dy, x0, x1) opens a free horizontal channel
    between lane rows 0 and 1 by moving lane rows >= 1 up by dy (outline H + dy) and reserving the channel rectangle
    x0..x1 (full channel height) against every stin/stk/nb placement; the neighbour head's feed-through stages live there."""
    global H,W,SHAPES
    H0,W0,S0=H,W,SHAPES
    geo=None
    if safe32 is not None:
        geo=safe32_geo(Path(__file__).resolve().parents[2],bool(channel),safe32)
        W,H,SHAPES=geo['W'],geo['H'],geo['shapes']
        if channel:channel=(geo['channel_dy'],*channel[1:])
    elif channel:H=round(H0+channel[0],6)
    try:return _plan(closed_pins,channel,perm,kt_x,score_x,geo)
    finally:H,W,SHAPES=H0,W0,S0


def _plan(closed_pins=None, channel=None, perm=None, kt_x=388.8, score_x=550.8, geo=None):
    root=Path(__file__).resolve().parents[2]
    views={'lane':('qkh_lane8_ref_b','ot_qkh_lane8'), 'ktree':('qkh_ktree_ref','ot_qkh_ktree'),
           'score':('qkh_native_score_1014','ot_qkh_head_score_native')}
    if geo:views=geo['views']
    fx=geo['front_dx'] if geo else 0.
    paths={k:(Path(closed_pins)/f'{cell}.lef' if closed_pins else
              root/'physical'/'ref_tile'/kit/'views'/cell/f'{cell}.lef')
           for k,(kit,cell) in views.items()}
    pins={k:read_pins(p) for k,p in paths.items()}
    def at(kind,r,names):return region([(r[0]+pins[kind][n][0],r[1]+pins[kind][n][1]) for n in names])

    fronts_q={g:(216.+fx+135.*g,5.4,129.6,43.2) for g in range(4)};kt=(kt_x,54.,*SHAPES['ktree']);score=(score_x,54.,*SHAPES['score'])
    dy=channel[0] if channel else 0.
    grid=[(43.2+172.8*c,54.+151.2*r+(dy if r>=1 else 0.),*SHAPES['lane']) for c in range(6) for r in range(3)
          if not (r==0 and c in (2,3))]
    if geo:
        kt=(*geo['kt'],*SHAPES['ktree']);score=(*geo['score'],*SHAPES['score'])
        grid=[(*g,*SHAPES['lane']) for g in geo['grid']]
    # KVPLAN2 2026-10-16 (perm): logical lane t sits in grid slot perm[t] (the closed ktree's kp_in groups run E -> W
    # with the lane index while the fronts run W -> E: identity put lane 15 957 um (pin regions) from its ktree group)
    lanes=({i:grid[perm[i]] if perm else r for i,r in enumerate(grid)} if not geo else
           {t:grid[perm[t]] if perm else grid[t] for t in range(16)})   # safe32: the grid may hold spare slots
    placed=list(fronts_q.values())+[kt,score]+list(lanes.values())
    keep=None
    if channel:
        # the channel's stage zone: row-0 lane top + CLEAR .. row-1 lane bottom - CLEAR (overlap() keeps every other child
        # CLEAR away from the zone, as from any child)
        y0=54.+129.6+CLEAR;y1=54.+151.2+dy-CLEAR
        if geo:   # safe32: the gap between lane rows 0 and 1 (grid rows from y0, pitch row_pitch)
            y0=geo['cfg']['y0']+SHAPES['lane'][1]+CLEAR;y1=geo['cfg']['y0']+geo['cfg']['row_pitch']+dy-CLEAR
        keep=(channel[1],y0,channel[2]-channel[1],y1-y0)
        placed.append(keep)
    free={k:list(candidates(SHAPES[k],placed)) for k in (['stin','stk','nb'] if not geo or geo['nb'] else ['stin','stk'])}
    rows=[];children={**{f'front{g}':r for g,r in fronts_q.items()},'ktree':kt,'score':score};hops=[]
    front_order=list(range(16))
    fronts={t:[(fronts_q[t//4][0]+32.4*(t%4),48.6),
               (fronts_q[t//4][0]+32.4*(t%4+1),48.6)] for t in lanes}
    # Place the farthest lanes first; every pin in each region is bounded.
    for t in sorted(lanes,key=lambda t:-lanes[t][1]):
        lane=lanes[t];x,y=lane[:2]
        li=at('lane',lane,[n for n in pins['lane'] if n.split('[')[0] in
            ('c_in','row_in','e_in','lt_in','hid','q_valid_in','q_beat_in','q_data_in')])
        lo=at('lane',lane,[n for n in pins['lane'] if n.split('[')[0] in ('kp','kpv','gf')])
        nb=at('lane',lane,[f'nb[{j}]' for j in range(64)])
        lr=at('lane',lane,['rst_n'])
        choices=[]
        for r in free['stin']:
            if any(overlap(r,f) for f in placed):continue
            a=bound(fronts[t],face(r,'E'));b=bound(face(r,'S'),li)
            c=bound(face(r,'S'),lr)
            choices.append((max(a,b,c),a+b+c,r,a,b,c))
        if not choices:raise ValueError('no stin placement')
        _,_,sin,a,b,c=min(choices);placed.append(sin);children[f'stin{t}']=sin
        hops.extend([(f'front->stin{t}',a),(f'stin{t}->lane{t}',b),(f'stin{t}.reset->lane{t}',c)])
        # The closed ktree north-face group for this unchanged logical lane index.
        kp=at('ktree',kt,[f'kp_in[{j}]' for j in range(32*t,32*(t+1))]+[f'gf_in[{t}]']+
              ([f'kpv_in[{t}]'] if f'kpv_in[{t}]' in pins['ktree'] else ['kpv_in'] if t==0 else []))
        choices=[]
        for r in free['stk']:
            if any(overlap(r,f) for f in placed):continue
            a=bound(lo,face(r,'N'));b=bound(face(r,'S'),kp)
            choices.append((max(a,b),a+b,r,a,b))
        if not choices:raise ValueError('no stk placement')
        _,_,stk,a,b=min(choices);placed.append(stk);children[f'stk{t}']=stk
        hops.extend([(f'lane{t}->stk{t}',a),(f'stk{t}->ktree',b)])
        if geo and not geo['nb']:   # static ASTK heads: no node beat, no nb1 / nb2 relays
            n1=n2=None
        else:
            # v1.1 assigned nb E-face region: 197.100..295.308 at 0.096 um/bit.
            target=[(W,197.1+0.096*64*t),(W,197.1+0.096*(64*t+63))]
            if perm:
                # KVPLAN2: the die's ASTK f<e><h> word for this lane sits at y (R0 / R180 heads) or H - y (MX / MY heads:
                # measured kvr2, lane 0 at 289..295 on h0): bound the last nb hop to both, so every orientation is short
                target=target+[(W,H-y) for _,y in target]
            lc=centre(nb);tc=centre(target)
            ideal1=tuple(lc[k]+(tc[k]-lc[k])/3 for k in range(2))
            ideal2=tuple(lc[k]+2*(tc[k]-lc[k])/3 for k in range(2))
            available=[r for r in free['nb'] if not any(overlap(r,f) for f in placed)]
            c1=[r for r in available if bound(nb,face(r,'W'))<=REACH]
            c2=[r for r in available if bound(face(r,'E'),target)<=REACH]
            dist=lambda r,p:abs(r[0]+r[2]/2-p[0])+abs(r[1]+r[3]/2-p[1])
            c1=sorted(c1,key=lambda r:dist(r,ideal1))[:100]
            c2=sorted(c2,key=lambda r:dist(r,ideal2))[:100]
            best=None
            for r1 in c1:
                a=bound(nb,face(r1,'W'))
                for r2 in c2:
                    if overlap(r1,r2):continue
                    b=bound(face(r1,'E'),face(r2,'W'));c=bound(face(r2,'E'),target)
                    # KVPLAN2 (perm plans): of the max-equal pairs, the one whose nb2 is nearest the head E-face target --
                    # the die-level nb hop (nb2 -> ASTK f<e><h>) continues from there (kvr2: 472 um with the sum rule)
                    trial=(max(a,b,c),c if perm else a+b+c,r1,r2,a,b,c)
                    if best is None or trial<best:best=trial
            if best is None:raise ValueError('no NB pair placement')
            _,_,n1,n2,a,b,c=best;placed.extend([n1,n2]);children[f'nb1_{t}']=n1;children[f'nb2_{t}']=n2
            hops.extend([(f'lane{t}->nb1_{t}',a),(f'nb1_{t}->nb2_{t}',b),(f'nb2_{t}->die_nb',c)])
        children[f'lane{t}']=lane
        rows.append(dict(lane=t,lane_xy_um=list(lane[:2]),stin=list(sin),stk=list(stk),
                         **(dict(nb1=list(n1),nb2=list(n2)) if n1 else {})))
    parent_inputs={'ti':[224.508+fx,673.212+fx], 'e':[686.076+fx,687.516+fx]}
    capture_pins={}
    ti_base=224.508+fx
    for g,r in fronts_q.items():
        x,y,w,h=r;caps={};ctrl_names=[f'c_in[{j}]' for j in range(4)]+[f'lt_in[{j}]' for j in range(12)]+['q_valid_in']+[f'q_beat_in[{j}]' for j in range(6)]
        ctrl_bits=list(range(4))+list(range(1028,1040))+[1040]+list(range(1041,1047))
        for j,(name,bit) in enumerate(zip(ctrl_names,ctrl_bits)):
            dest=(x,y+5.052+0.096*j);src=(ti_base+0.288*bit,0.)
            caps[name]=dict(face='W',layer='M4',slot_xy_um=list(dest),parent_ti_bit=bit)
            hops.append((f'die_ti[{bit}]->front{g}.{name}',bound([src],[dest])))
        for j in range(256):
            bit=4+256*g+j;dest=(x+52.572+0.096*j,y);src=(ti_base+0.288*bit,0.)
            caps[f'row_in[{j}]']=dict(face='S',layer='M5',slot_xy_um=list(dest),parent_ti_bit=bit)
            hops.append((f'die_ti[{bit}]->front{g}.row[{j}]',bound([src],[dest])))
        for j in range(512):
            bit=1047+j;dest=(x if j%2==0 else x+w,y+8.892+0.096*(j//2));src=(ti_base+0.288*bit,0.)
            caps[f'q_data_in[{j}]']=dict(face='W' if j%2==0 else 'E',layer='M4',slot_xy_um=list(dest),parent_ti_bit=bit)
            hops.append((f'die_ti[{bit}]->front{g}.q[{j}]',bound([src],[dest])))
        for j in range(16):
            dest=(x+w,y+3.036+0.096*j);src=(686.076+fx+0.096*j,0.)
            caps[f'e_in[{j}]']=dict(face='E',layer='M4',slot_xy_um=list(dest),parent_e_bit=j)
            hops.append((f'die_e[{j}]->front{g}',bound([src],[dest])))
        capture_pins[g]=caps
    score_target=[(706.092+fx,0.),(709.26+fx,0.)]
    for g,r in fronts_q.items():hops.append((f'front{g}.pack_fault->score4',bound(face(r,'N'),face(score,'N'))))
    hops.extend([('ktree->score4',bound(at('ktree',kt,[n for n in pins['ktree'] if n.split('[')[0] in ('sc_d','sc_f','g_f')]),face(score,'W'))),
                 ('score4->die_s',bound(face(score,'E'),score_target)),
                 ('score4.kt_rst_n->ktree',bound(face(score,'W'),at('ktree',kt,['rst_n'])))])
    ov=[(a,b) for a,b in itertools.combinations(children,2) if overlap(children[a],children[b])]
    if keep:ov+=[('channel',n) for n in children if overlap(keep,children[n])]
    if keep and geo:   # the stage leaves themselves must fit the zone
        sy=keep[1]+(keep[3]-21.6)/2
        for nm,r in (('ftg',(keep[0]+CLEAR,sy,324.,21.6)),('fts',(keep[0]+334.8,sy,21.6,21.6))):
            if r[0]+r[2]>keep[0]+keep[2]+1e-6 or r[1]<keep[1]-1e-6 or r[1]+r[3]>keep[1]+keep[3]+1e-6:ov.append((nm,'channel zone'))
    outside=[n for n,r in children.items() if r[0]<0 or r[1]<0 or r[0]+r[2]>W+1e-6 or r[1]+r[3]>H+1e-6]
    clocks=[dict(child=n,rtl_clock=('ck_score' if n=='score' else 'ck_kt' if n=='ktree' else
             f"ck_{'nb1' if n.startswith('nb1_') else 'nb2' if n.startswith('nb2_') else ''.join(c for c in n if not c.isdigit())}[{n.split('_')[-1] if '_' in n else ''.join(c for c in n if c.isdigit())}]"),
             child_clock_pin='clk',clock_pin_assignment='actual leaf pin required at hardening') for n in children]
    for entry in clocks:
        n=entry['child'];kind='lane' if n.startswith('lane') else n
        if kind in pins:
            r=children[n];xy=pins[kind]['clk']
            entry.update(clock_pin_assignment='exported closed-view pin',
                         slot_xy_um=[round(r[0]+xy[0],6),round(r[1]+xy[1],6)])
    assert len(children)==len(clocks)==(54 if geo and not geo['nb'] else 86)
    worst=max(hops,key=lambda h:h[1]);valid=not ov and not outside and worst[1]<=REACH
    return dict(schema='qwen-kvsys-head-native-plan/r4',slot='qkd_rhead',contract='kvsys_v1.1',
        slot_outline_um=[W,H],canonical_orientation='R0; control face S',clock_entries_per_head=len(clocks),
        rtl_master='ot_qkh_head_native_r4' if not geo else 'ot_qkh_head_native_r4_s_lk_nc32c / _r4_ft_s_lk_nc32c',
        **({'safe32':dict(flag='OT_KV_QKH_SAFE32',geometry=geo['cfg'],leaf_sizes_um={k:list(v) for k,v in SHAPES.items()
                                                                                      if k in ('lane','ktree','score','stin','stk','front')},
                         front_dx_um=fx,note='nb1 / nb2 absent: static ASTK heads carry no node beat')} if geo else {}),latency_change_cycles=0,
        reach_method='maximum Manhattan distance between every endpoint of the assigned pin regions',
        reach_rule_um=REACH,**({'lane_slot_perm':list(perm)} if perm else {}),
        **({'internal_worst_hop':dict(zip(('name','um'),max(((n,round(d,3)) for n,d in hops if not n.startswith(('die_ti','die_e'))),key=lambda h:h[1])))}
           if perm else {}),valid=valid,worst_hop=dict(name=worst[0],um=round(worst[1],3)),
        overlaps=ov,outside=outside,front_port_order_W_to_E=front_order,
        shared_children={n:list(children[n]) for n in ['front0','front1','front2','front3','ktree','score']},lanes=sorted(rows,key=lambda r:r['lane']),
        children={n:list(r) for n,r in children.items()},clock_entries=clocks,
        parent_data_pin_assignments=dict(front_S_bit_matched=parent_inputs,
            parent_score_output_S=list(score_target),front_capture_status='exact proposed per-bit assignments; exported views still required'),
        reset_rule='preserve the RTL reset topology; assign the external asynchronous reset distribution '
                   'and measure recovery/removal and native reset paths before physical qualification',
        front_capture_pins=capture_pins,
        closed_pin_sources={k:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in paths.items()},
        hops=[dict(name=n,um=round(d,3)) for n,d in hops],
        qualification='exact proposed per-bit input pins and closed leaf pins; fresh front/score4 views, physical pin replay and native pair reach required before qualification',
        feedthrough_channel=(dict(dy_um=dy,rect_um=list(keep),purpose='kvsys v1.4.3 near-head feed-through: the far neighbour head T1 / S2 stages',
                                  # safe32: the T1 (gather 324 x 21.6) / S2 (sstage 21.6^2) homes the die and kv_expand take (v1.1 rule:
                                  # x0 + 5.4 / x0 + 334.8, centred in the channel zone; kv_die.V143_FT)
                                  **({'stage_xy_um':dict(ftg=[round(keep[0]+CLEAR,6),round(keep[1]+(keep[3]-21.6)/2,6)],
                                                         fts=[round(keep[0]+334.8,6),round(keep[1]+(keep[3]-21.6)/2,6)])} if geo else {}))
                             if keep else None))

def main():
    a=argparse.ArgumentParser();a.add_argument('out',type=Path);a.add_argument('--closed-pins',type=Path)
    a.add_argument('--channel',help='v1.4.3 feed-through channel DY,X0,X1 (um)')
    a.add_argument("--reach",type=float,default=500);a.add_argument('--ktree-x',type=float,default=388.8);a.add_argument('--score-x',type=float,default=550.8)
    a.add_argument('--perm',help='lane -> grid slot, 16 comma-separated ints')
    a.add_argument('--safe32',action='store_true',help='KV-BIND12: nc32c lane / ktree grid (SAFE32); --channel DY is then SAFE32 channel_dy')
    a.add_argument('--safe32-cfg',default='{}',help='JSON overrides of SAFE32 (e.g. the alt_5x4 grid)')
    args=a.parse_args();global REACH;REACH=args.reach
    r=plan(args.closed_pins,tuple(map(float,args.channel.split(','))) if args.channel else None,
           [int(v) for v in args.perm.split(',')] if args.perm else None,args.ktree_x,args.score_x,
           json.loads(args.safe32_cfg) if args.safe32 else None)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['valid','clock_entries_per_head','worst_hop','internal_worst_hop','overlaps','outside'] if k in r}))
    return 0 if r['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
