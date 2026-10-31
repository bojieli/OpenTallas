import json,sys,matplotlib
matplotlib.use("Agg");import matplotlib.pyplot as plt
sys.path.insert(0,"tools/die_plan")
import schema as S
import taps as TP
from pathlib import Path
P=json.load(open(sys.argv[1]));PP=S.Plan(P,Path(sys.argv[1]).parent/'die_plan.json');out=sys.argv[2];Ts=sys.argv[3].split(",")
fig,ax=plt.subplots(1,len(Ts),figsize=(3.4*len(Ts),7))
for a,T in zip(ax,Ts):
    t=P['partition_types'][T];w,h=t['outline_um'];lc=t['clock'].get('landing_contract',{})
    for r in lc.get('bands',{}).values():
        x0,y0,x1,y1=r['rect_um'];a.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fc='orange',alpha=.35,ec='none'))
    for x0,y0,x1,y1 in S.placed_macro_boxes(t).values():
        a.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fc='lightblue',ec='b',lw=.5))
    D=TP.density_taps(PP,T) if t['clock'].get('tap_mode')=='density' else [(p.get('name'),p['xy'][0],p['xy'][1],0,0) for p in t['clock']['taps']]
    tx=[d[1] for d in D];ty=[d[2] for d in D];mx=max([d[3] for d in D] or [0])
    a.plot(tx,ty,'r+',ms=5,label='clock taps')
    for s in t['ft_slots']:
        for x,y in (s.get('regs_um') or [])[1:]: a.plot(x,y,'g^',ms=4)
    for n,(x0,y0,x1,y1) in (lc.get('group_rects_um') or {}).items():
        a.add_patch(plt.Rectangle((x0-6,y0-6),x1-x0+12,y1-y0+12,fc='m',ec='m'))
    for r in (lc.get('collector_tree') or {}).get('relays',[]): a.plot(*r['xy'],'k.',ms=1.5)
    a.add_patch(plt.Rectangle((0,0),w,h,fc='none',ec='k'))
    a.set_xlim(-10,w+10);a.set_ylim(-10,h+10);a.set_aspect('equal')
    a.set_title(f"{T[:24]}\n{len(tx)} {t['clock'].get('tap_mode')} taps max {mx} sinks; ^ ft station, magenta collector box",fontsize=7);a.tick_params(labelsize=5)
plt.tight_layout();plt.savefig(out,dpi=110)
