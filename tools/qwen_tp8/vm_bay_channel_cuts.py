#!/usr/bin/env python3
"""VM6 2026-10-14: cut arithmetic of the bay channels of the tile-level lane plan (vm_bay_tiles_claude.json): per inner 4.32-um
channel, the pins that must ESCAPE (not straight pin-to-pin same-bit) vs the horizontal tracks over the pin band
(M6 at 0.064 with the 31.7 % GRT reduction seen in bp2; + M8 at 0.080, 94.7 %).  Run from the repo root."""
import json,collections,sys
T=json.load(open('results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json'))
CAP_M6=1/0.064*(1-0.317); CAP_M8=1/0.08*0.947
SPAN={'E':57.0,'W':57.0,'P':83.0}
use=collections.defaultdict(lambda: collections.Counter())  # (bay,slot) -> face -> pins
straight=collections.Counter()
for lane,chain in T['lane_chain'].items():
    for c in chain:
        tl=c['tiles']
        for j,t in enumerate(tl):
            k=t['kind']; din='W' if k in 'EP' else 'E'; qout='E' if k in 'EP' else 'W'
            use[(c['bay'],t['slot'])][din]+=8; use[(c['bay'],t['slot'])][qout]+=8
            if j+1<len(tl):
                n=tl[j+1]
                if n['slot']==t['slot']+1 and k in 'EP' and n['kind'] in 'EP' and n['bit0']==t['bit0']: straight[(c['bay'],t['slot'])]+=8
rows=[]
for bay,tiles in T['bay_tiles'].items():
    sl={t['slot']:t['kind'] for t in tiles}
    for s in sorted(sl):
        if s+1 in sl:
            esc=use[(bay,s)]['E']+use[(bay,s+1)]['W']-2*straight[(bay,s)]
            span=min(SPAN[sl[s]],SPAN[sl[s+1]])
            rows.append((bay,s,esc,esc/(span*CAP_M6),esc/(span*(CAP_M6+CAP_M8))))
n=len(rows)
print('inner 4.32-um channels:',n,' tiles',sum(len(t) for t in T['bay_tiles'].values()))
for lim in (0.6,0.8,1.0):
    print(f' ratio > {lim}:  M2-M7 (probe) {sum(r[3]>lim for r in rows)}   with M8 {sum(r[4]>lim for r in rows)}')
print(' worst',sorted(rows,key=lambda r:-r[4])[:5])
print(' pad15s0',[r for r in rows if r[0]=='vm_pad_15_S0'])
tot=sum(r[2] for r in rows); st=sum(straight.values())
print(' straight-through bits (pin-to-pin across a channel):',st,' escape pins in channels:',tot)
