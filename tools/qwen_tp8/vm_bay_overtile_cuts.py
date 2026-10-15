#!/usr/bin/env python3
"""VM6 2026-10-14: over-tile horizontal crossing demand per tile of the tile-level lane plan (bits whose wire passes over the
tile middle: only M6 / M8 run horizontally over an M1-M5-blocked tile).  Run from the repo root."""
import json,collections
T=json.load(open('results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json')); plan=json.load(open('results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json'))
bays={b['n']:b for b in plan['x_relay_bays']}; ch={c['n']:c for c in plan['children']}
TW,G=17.28,4.32; P=TW+G
cxy=lambda o:(o['x']+o['w']/2,o['y']+o['h']/2)
def face(B,o,col=False):
    if col: return 'n' if o['y']>B['y'] else 's'
    bc=cxy(B); x,y=cxy(o); dx,dy=x-bc[0],y-bc[1]
    return ('e' if dx>0 else 'w') if abs(dx)>=abs(dy) else ('n' if dy>0 else 's')
cross=collections.Counter(); kinds={}
for bay,tl in T['bay_tiles'].items():
    for t in tl: kinds[(bay,t['slot'])]=t['kind']
for name,chain in T['lane_chain'].items():
    chain=sorted(chain,key=lambda c:c['visit']); src,pl=name.split('>')
    for i,c in enumerate(chain):
        B=bays[c['bay']]; n=B['tiles']
        fi=face(B,bays[chain[i-1]['bay']]) if i else face(B,ch[src])
        fo=face(B,bays[chain[i+1]['bay']]) if i+1<len(chain) else face(B,ch[f'vm_xcol_{pl[1:]}'],col=True)
        # x positions in slot units: tile s spans [s, s+0.8]; mid at s+0.4; W edge -0.5, E edge n-0.5+... 
        def fx(f,first_slot): return {'w':-1,'e':n}.get(f,first_slot)
        pos=[fx(fi,c['tiles'][0]['slot'])]
        for t in c['tiles']:
            s=t['slot']; k=t['kind']; d=s if k in 'EP' else s+1; q=s+1 if k in 'EP' else s
            pos+= [d-0.1, q-0.1]   # pin x in slot units (channel just left of slot boundary)
        pos.append(fx(fo,c['tiles'][-1]['slot']))
        for a,b in zip(pos[::2],pos[1::2]):   # wire segments: entry->d, q->d, ..., q->exit
            lo,hi=min(a,b),max(a,b)
            for s in range(n):
                if lo < s+0.4 < hi and (c['bay'],s) in kinds: cross[(c['bay'],s)]+=8
cap_m6=97.2/0.064*(1-0.317); cap_m8=97.2/0.08*0.947
v=sorted(cross.values()); N=len(kinds)
print('tiles',N,'max crossing',v[-1],'p95',v[int(.95*len(v))])
for lim in (0.6,0.8,1.0):
    print(f' over-tile ratio > {lim}: M6 only {sum(x/cap_m6>lim for x in v)}  M6+M8 {sum(x/(cap_m6+cap_m8)>lim for x in v)}')
print(' pad15s0',{k[1]:x for k,x in cross.items() if k[0]=='vm_pad_15_S0'})
