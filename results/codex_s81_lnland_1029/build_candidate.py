#!/usr/bin/env python3
"""Exact PG-aware one-clock LN candidate; source model only, no qualification."""
import bisect, json, math, sys
from pathlib import Path
B=Path(__file__).resolve().parent; R=B.parents[1]
sys.path.insert(0,str(R/'tools/die_plan'))
import schema as S
W=112.32; lo=6.144; hi=W-lo; mod='ot_s81_mu72_lnland_nst_1ck'
groups={'W':(['k_lo_v']+[f'k_lo_d[{i}]' for i in range(553)]+['k_li_r','k_rxv'],'INPUT'),
'S':(['k_lo_r','k_li_v']+[f'k_li_d[{i}]' for i in range(553)]+[f'k_flt[{i}]' for i in range(3)],'OUTPUT'),
'E':(['n_lo_r','n_li_v']+[f'n_li_d[{i}]' for i in range(553)]+[f'n_flt[{i}]' for i in range(3)],'INPUT'),
'N':(['n_lo_v']+[f'n_lo_d[{i}]' for i in range(553)]+['n_li_r','n_rxv'],'OUTPUT')}
pins=[]; dirs={}; report={}
for face,(names,direction) in groups.items():
    layer='M4' if face in 'WE' else 'M5'; pitch=.048; offset=.012
    tracks=[k for k in range(math.ceil((lo-offset)/pitch),math.floor((hi-offset)/pitch)+1) if not S.pg_blocked(layer,offset+k*pitch)]
    chosen=S.spread(tracks,len(names),(lo-offset)/pitch,(hi-offset)/pitch)
    coords=[round(offset+tracks[k]*pitch,6) for k in chosen]
    for name,c in zip(names,coords):
        x,y=(.042,c) if face=='W' else ((W-.042,c) if face=='E' else ((c,.042) if face=='S' else(c,W-.042)))
        pins.append(dict(name=name,layer=layer,x=x,y=y)); dirs[name]=direction
    mx=max(bisect.bisect_left(coords,c+10-1e-9)-i for i,c in enumerate(coords))
    report[face]=dict(bits=len(names),max_pins_in_10um=mx,limit=64,usable_tracks=len(tracks),track_fraction=len(names)/len(tracks))
    assert mx<=64 and len(names)/len(tracks)<=.6
for n,x in [('rs_k',4.332),('rs_n',107.964),('ck_k',56.172)]:
    pins.append(dict(name=n,layer='M5',x=x,y=56.16 if n=='ck_k' else .042)); dirs[n]='INPUT'
assert len(pins)==2231 and len({(p['layer'],p['x'],p['y']) for p in pins})==2231
(B/'pins.json').write_text(json.dumps(dict(module=mod,outline_um=[W,W],pins=pins),indent=1)+'\n')
lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {mod}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {W} BY {W} ;',' SYMMETRY X Y ;']
for p in pins:
    n,L,x,y=p['name'],p['layer'],p['x'],p['y']; dx,dy=(.024,.24) if n=='ck_k' else ((.024,.042) if L=='M5' else(.042,.016))
    lef += [f' PIN {n}',f'  DIRECTION {dirs[n]} ;','  USE CLOCK ;' if n=='ck_k' else '  USE SIGNAL ;','  PORT',f'   LAYER {L} ;',f'   RECT {x-dx:.6f} {y-dy:.6f} {x+dx:.6f} {y+dy:.6f} ;','  END',f' END {n}']
lef += [f'END {mod}','END LIBRARY'];(B/f'{mod}.lef').write_text('\n'.join(lef)+'\n')
(B/'pin_allocation.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps(report))
