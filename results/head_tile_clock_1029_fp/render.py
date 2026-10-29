import json,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
exec(open('audit.py').read().split("if __name__")[0])
d=json.load(open('run3/reg_spine_plan.json'));T={t['id']:t for t in d['taps']}
ids=[4,9,14,37,38,43];fig,ax=plt.subplots(2,3,figsize=(15,9))
for a,i in zip(ax.flat,ids):
    t=T[i];w=9
    for m in mac:a.add_patch(Rectangle((m[0],m[1]),m[2]-m[0],m[3]-m[1],color='0.6'))
    for b in blk:a.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],color='orange',alpha=.5))
    for r in rows:
        if abs(r[1]-t['y'])<w: a.plot([r[0],r[2]],[r[1],r[1]],lw=.3,color='b')
    for nm,r in rects(t):a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='r' if nm=='drv' else 'g',ec='k',lw=.3))
    a.set_xlim(t['x']-14,t['x']+6);a.set_ylim(t['y']-w/2,t['y']+w/2);a.set_title(f"tap {i} pad {t['pad']} fold={bool(t.get('pad_xy'))} move={t.get('footprint_move_um')}")
plt.tight_layout();plt.savefig('fold.png',dpi=80)
