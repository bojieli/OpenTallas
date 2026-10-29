#!/usr/bin/env python3
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import schema as S,gen_phys as G,taps
path=Path(sys.argv[1]);P=S.Plan(S.load(path),path);out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
T=['hd_st_k5','hd_st_m','hd_st_n3_transit','hd_st_n3_turn','hd_st_n4','hd_st_str','hd_st_turn','hd_turn_a','hd_turn_b']
if len(sys.argv)>3:T=sys.argv[3].split(',')
fig,axs=plt.subplots(3,3,figsize=(18,12)) if len(T)>3 else plt.subplots(1,len(T),figsize=(8*len(T),6),squeeze=False)
report={}
for ax,tn in zip(axs.flat,T):
 t=P.types[tn];w,h=t['outline_um'];pin={(b,i):(x,y) for b,i,l,x,y,f in G.type_pins(P,tn)}
 ax.plot([0,w,w,0,0],[0,0,h,h,0],c='black',lw=1)
 for s in t['ft_slots']:
  b=s['width']//2;seq=[pin[(s['name']+'_i',b)]]+[(v[b][0]+1.08,v[b][1]+.135) for v in s['bit_sites_um']]+[pin[(s['name']+'_o',b)]]
  ax.plot([v[0] for v in seq],[v[1] for v in seq],'.-',label=s['name'],lw=.8,ms=3)
  # Endpoint-band strips expose density rather than plotting all routed wires.
  for suffix in ('_i','_o'):
   pts=[xy for (n,i),xy in pin.items() if n==s['name']+suffix]
   ax.scatter([p[0] for p in pts],[p[1] for p in pts],s=.2,c='black',alpha=.4)
 ck=G.clock_pins(P,tn);ax.scatter([x for _,x,y in ck],[y for _,x,y in ck],c='crimson',s=12,marker='+',label='clock')
 cs=taps.control_pin_sinks(P,tn)
 if cs:ax.scatter([x for _,x,y in cs],[y for _,x,y in cs],c='purple',s=18,marker='x',label='reset/start')
 mr=max((min(abs(x-a)+abs(y-b) for _,a,b in ck) for _,x,y in cs),default=0)
 report[tn]={'clock_taps':len(ck),'control_max_tap_reach_um':round(mr,3)}
 ax.set(title=f'{tn}: {w:g} x {h:g} um',aspect='equal');ax.legend(fontsize=6,loc='upper left',ncol=2);ax.grid(alpha=.15)
fig.suptitle('HEAD hk5 pure FT face stations: center-bit paths; black endpoint bands, + clock, x reset/START',fontsize=12)
fig.tight_layout();fig.savefig(out,dpi=150);out.with_suffix('.json').write_text(json.dumps(report,indent=1)+'\n')
