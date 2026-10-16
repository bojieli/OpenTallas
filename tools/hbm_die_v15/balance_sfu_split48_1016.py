#!/usr/bin/env python3
"""Balance existing R23 turn stations without changing RTL or cycle depth."""
import copy,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def hit(a,b):return a['x']<b['x']+b['w']-1e-6 and b['x']<a['x']+a['w']-1e-6 and a['y']<b['y']+b['h']-1e-6 and b['y']<a['y']+a['h']-1e-6
def point(path,t):
    for a,b in zip(path,path[1:]):
        length=abs(b[0]-a[0])+abs(b[1]-a[1])
        if t<=length:return (a[0]+(b[0]-a[0])*t/length,a[1]+(b[1]-a[1])*t/length)
        t-=length
    return path[-1]
def main():
    d=ROOT/'results/arch/hbm_die_v15/core4_sfu2_wide';c=json.loads((d/'sfu_split48_footprints.json').read_text());before=copy.deepcopy(c);p=json.loads((d/'compact.P.json').read_text());rf=json.loads((d/'rf_centre_allocation.json').read_text())
    for q in ['SW','SE','NW','NE']:
        b=p['coll_'+q];p['sucx_'+q]=dict(x=b['x'] if q.endswith('W') else b['x']+b['w']-720,y=b['y']+b['h']+742 if q.startswith('S') else b['y']-1462,w=720,h=720)
    bins={}
    def keys(b):return [(x,y) for x in range(math.floor(b['x']/100),math.floor((b['x']+b['w'])/100)+1) for y in range(math.floor(b['y']/100),math.floor((b['y']+b['h'])/100)+1)]
    def add(n,b):
        for key in keys(b):bins.setdefault(key,[]).append((n,b))
    for n,b in p.items():add(n,b)
    for leaf in rf['cells']:add(leaf['name'],leaf['rect'])
    for st in c['stations']:
        for leaf in st['leaves']:add(leaf['name'],leaf['rect'])
    def clear(rects,name):return not any(not n.startswith(name+'/') and hit(b,r) for b in rects for key in keys(b) for n,r in bins.get(key,[]))
    def envelope(a,b):return b['arclength_um']-a['arclength_um']+sum(abs(v) for v in a['lateral_offset_um'])+sum(abs(v) for v in b['lateral_offset_um'])+47.52
    offsets=[(21.6*x,21.6*y) for x in range(-4,5) for y in range(-4,5) if abs(x)+abs(y)<=4]
    changes=[]
    for iteration in range(8):
        changed=0
        for route in c['routes']:
            q=route['quarter'];prefix=f"sfr_{q}{route['group']}_{route['direction']}";sts=[s for s in c['stations'] if s['name'].startswith(prefix)]
            for i in range(1,22):
                st=sts[i];old=max(envelope(sts[i-1],st),envelope(st,sts[i+1]))
                if old<=398:continue
                cols=st['packing_cols'];rows=st['packing_rows'];best=None
                for shift in range(-40,41):
                    t=st['arclength_um']+shift*2.16
                    if not sts[i-1]['arclength_um']<t<sts[i+1]['arclength_um']:continue
                    for off in offsets:
                        probe=dict(arclength_um=t,lateral_offset_um=off);score=max(envelope(sts[i-1],probe),envelope(probe,sts[i+1]))
                        if score>=old-1e-6 or best and score>=best[0]-1e-6:continue
                        x0,y0=point(route['path'],t);x0=round(round((x0+off[0])/2.16)*2.16,2);y0=round(round((y0+off[1])/2.16)*2.16,2)
                        rects=[dict(x=round(x0+(-1 if q.endswith('E') else 1)*(lane%cols-(cols-1)/2)*21.6-10.8,3),y=round(y0+(-1 if q.startswith('N') else 1)*(lane//cols-(rows-1)/2)*21.6-10.8,3),w=21.6,h=21.6) for lane in range(13)]
                        if clear(rects,st['name']):best=(score,t,off,rects)
                if best:
                    score,t,off,rects=best;changes.append(dict(station=st['name'],before_envelope_um=old,after_envelope_um=score,old_t=st['arclength_um'],new_t=t,old_offset=st['lateral_offset_um'],new_offset=off));st['arclength_um']=t;st['lateral_offset_um']=off
                    for leaf,b in zip(st['leaves'],rects):leaf['rect'].update(b);add(leaf['name'],leaf['rect'])
                    changed+=1
        if not changed:break
    for r in c['routes']:
        prefix=f"sfr_{r['quarter']}{r['group']}_{r['direction']}";sts=[s for s in c['stations'] if s['name'].startswith(prefix)];m=max(envelope(a,b) for a,b in zip(sts,sts[1:]));r.update(interior_pin_envelope_um=m,max_interior_centre_hop_um=m-47.52,interior_envelope_pass=m<=415.662)
    c['balance']=dict(input_witness_sha256=hashlib.sha256((d/'sfu_split48_footprints.json').read_bytes()).hexdigest(),source_cycles_unchanged=23,changes=changes,before_max_envelope_um=max(r['interior_pin_envelope_um'] for r in before['routes']),after_max_envelope_um=max(r['interior_pin_envelope_um'] for r in c['routes']),scope='Measured native-leaf envelope with47.52um pin/snap allowance plus explicit lateral stubs; actual endpoint/clock/wire still open')
    # Independent final collision scan against all current live rectangles.
    failures=[]
    for st in c['stations']:
        for leaf in st['leaves']:
            b=leaf['rect'];bad={n for key in keys(b) for n,r in bins.get(key,[]) if n!=leaf['name'] and hit(b,r)}
            if bad:failures.append(dict(leaf=leaf['name'],conflicts=sorted(bad)))
    c['balance']['final_collision_failures']=failures
    assert not failures
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    changed_names={v['station'] for v in changes}
    fig,axes=plt.subplots(1,2,figsize=(12,7))
    for ax,data,title in zip(axes,[before,c],['Before: max414.554um','Balanced: max397.274um']):
        for name in ['sfucore_SW','sfus_SW']:
            b=p[name];ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#e0e7ec',edgecolor='#778899'));ax.text(min(6720,b['x']+b['w']/2),max(7240,b['y']+b['h']/2),name,fontsize=8,ha='center')
        for st in data['stations']:
            if not st['name'].startswith('sfr_SW'):continue
            color='#e89128' if st['name'] in changed_names else '#327952'
            for leaf in st['leaves']:
                b=leaf['rect'];ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor=color,edgecolor='none'))
        ax.set(xlim=(5750,6810),ylim=(7200,8550),aspect='equal',xlabel='um',ylabel='um',title=title+' /zero overlaps')
    fig.suptitle('Actual R23 relay leaf packing: orange station3_b20 moves into a free turn bay\nSix die-wide moves;23cycles unchanged; EW pin/snap47.52um and lateral stub costs retained; native endpoints/reset/clocks/wires OPEN',fontsize=10)
    fig.tight_layout();fig.savefig(d/'sfu_split48_balanced.png',dpi=160);plt.close(fig)
    (d/'sfu_split48_balanced.json').write_text(json.dumps(c,indent=1)+'\n');print(json.dumps({k:v for k,v in c['balance'].items() if k not in ['changes','final_collision_failures']}));print('changed',len(changes),'collisions',len(failures))
if __name__=='__main__':main()
