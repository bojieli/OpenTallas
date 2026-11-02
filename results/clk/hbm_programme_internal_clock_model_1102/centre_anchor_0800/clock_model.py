"""Private native single-input clock geometry PREP; never writes RTL or a kit."""
import csv, json, re, sys, pathlib, hashlib, functools
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import taps
R=pathlib.Path(__file__).parent; I=R/'input'
def read(n): return json.loads((I/n).read_text())
@functools.lru_cache(None)
def lef(path,master,pin):
    text=path.read_text(); b=text.split('MACRO '+master+'\n',1)[1].split('END '+master,1)[0]
    w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',b).groups())
    p=b.split('PIN '+pin+'\n',1)[1].split('END '+pin,1)[0]
    rr=[list(map(float,x)) for x in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',p)]
    assert rr
    return w,h,[min(q[0] for q in rr),min(q[1] for q in rr),max(q[2] for q in rr),max(q[3] for q in rr)]
model=read('model.json'); gate=read('clock_entry_gate.json'); sm=read('source_clock_sink_map.json')
rows=list(csv.DictReader((I/'actual_FF_rows.csv').open()))
ff={x['cell']:x for x in rows}; macros={x['name']:x for x in model['macros']}
assert len(ff)==20842 and len(macros)==44 and len(sm)==20886
norm=lambda s:s.replace('\\','').strip()
ff={norm(k):v for k,v in ff.items()}; macros={norm(k):v for k,v in macros.items()}
sinks=[]; names=set(); matched=[]
for s in sm:
    n=norm(s['instance']); assert n not in names; names.add(n)
    assert s['source_clock_port']==s['actual_net']=='clk'
    w,h,p=lef(I/('std.lef' if s['kind']=='FF' else 'macro.lef'),s['master'],s['pin'])
    if s['kind']=='FF':
        f=ff[n]; x,y=float(f['x_um'])-w/2,float(f['y_um'])-h/2
        # Union R0/MX clock metal; no guessed orientation or centre-only credit.
        p=[p[0],min(p[1],h-p[3]),p[2],max(p[3],h-p[1])]
    else:
        m=macros[n]; x,y=m['rect_um'][:2]
        assert abs(m['rect_um'][2]-x-w)<1e-6 and abs(m['rect_um'][3]-y-h)<1e-6
    q=[p[0]+x,p[1]+y,p[2]+x,p[3]+y]
    sinks.append([(q[0]+q[2])/2,(q[1]+q[3])/2,1])
    matched.append(dict(instance=n,kind=s['kind'],pin=s['pin'],rect_um=q))
assert len(names)==len(ff)+len(macros)
W,H=model['outline_um']; cw,ch=1.62,.27
# Full BUFx24 root landing reservation on actual native lower-left grid.
xx=np.arange(4.32,W-4.32-cw+1e-7,2.16)+cw/2
yy=np.arange(4.32,H-4.32-ch+1e-7,.27)+ch/2
X,Y=np.meshgrid(xx,yy); clear=np.ones(X.shape,dtype=bool)
def forbid(b):
    ix=np.where((xx+cw/2>b[0]+1e-8)&(xx-cw/2<b[2]-1e-8))[0]
    iy=np.where((yy+ch/2>b[1]+1e-8)&(yy-ch/2<b[3]-1e-8))[0]
    if len(ix) and len(iy): clear[np.ix_(iy,ix)]=False
for m in macros.values():
    a,b,c,d=m['rect_um'];forbid([a-4.32,b-4.32,c+4.32,d+4.32])
for f in ff.values():
    x,y=float(f['x_um']),float(f['y_um']);forbid([x-.702,y-.135,x+.702,y+.135])
forbid(gate['entry_island_um'])
sites=np.stack([X[clear],Y[clear]],axis=1); assert len(sites)
used=[]
def reserve(px,py,group):
    d=np.abs(sites[:,0]-px)+np.abs(sites[:,1]-py)
    # Exact four transformed extrema of the full pin rectangles, not a
    # centre-only approximation; computes the same max L1 as the loop below.
    ulo=min(q[0]+q[1] for q in group);uhi=max(q[2]+q[3] for q in group)
    vlo=min(q[0]-q[3] for q in group);vhi=max(q[2]-q[1] for q in group)
    u=sites[:,0]+sites[:,1];v=sites[:,0]-sites[:,1]
    far=np.maximum.reduce([u-ulo,uhi-u,v-vlo,vhi-v])
    candidates=np.where(far<=220+1e-6)[0]
    for j in candidates[np.argsort(d[candidates],kind='stable')]:
        x,y=sites[j]
        if not np.isfinite(d[j]): continue
        if any(abs(x-a)<cw-1e-8 and abs(y-b)<ch-1e-8 for a,b in used): continue
        radius=max(max(abs(q[k]-x)+abs(q[l]-y) for k in (0,2) for l in (1,3)) for q in group)
        if radius<=220+1e-6:
            used.append((float(x),float(y))); return float(x),float(y),radius
        if d[j]>80: break
    return None
pending=[list(range(len(sinks)))]; leaves=[]
while pending:
    ids=pending.pop(); pts=[sinks[k] for k in ids]
    px=taps._wmedian(pts,0);py=taps._wmedian(pts,1)
    p=reserve(px,py,[matched[k]['rect_um'] for k in ids]) if len(ids)<=1200 else None
    if p:
        leaves.append(dict(name='regional_'+str(len(leaves)),xy_um=p[:2],sink_count=len(ids),max_full_pin_L1_um=p[2],sink_indices=ids,reserved_master='BUFx24_ASAP7_75t_R',reservation_um=[p[0]-cw/2,p[1]-ch/2,p[0]+cw/2,p[1]+ch/2]))
    else:
        assert len(ids)>1, ('unplaceable actual sink', matched[ids[0]])
        axis=max((0,1),key=lambda a:max(sinks[i][a] for i in ids)-min(sinks[i][a] for i in ids))
        ids.sort(key=lambda i:(sinks[i][axis],sinks[i][1-axis],i)); k=len(ids)//2
        pending.extend([ids[k:],ids[:k]])
out=dict(status='DISABLED_NATIVE_INTERNAL_CLOCK_GEOMETRY_PREP',source='Exact0525 scalar clk graph; candidate actual rows + snapped macro geometry',outline_um=[W,H],public_clock_inputs=1,entry=gate['full_shapes'],entry_island_um=gate['entry_island_um'],native_sinks=dict(FF=len(ff),SRAM=len(macros),total=len(sm)),regional_root_count=len(leaves),max_regional_load=max(x['sink_count'] for x in leaves),max_full_pin_L1_um=max(x['max_full_pin_L1_um'] for x in leaves),regional_design_target=1200,regional_hard_planning_cap=1500,regional_radius_um=220,roots=leaves,sinks=matched,root_reservation='One real BUFx24 landing per region; downstream CTS cells/PG and electrical fanout unqualified, not a single1500-sink driver claim',structured_topology='Single primary clk -> balanced native CTS branching -> these regional local CTS subtrees. No new public ports or source clock splitting. CTS must balance root-to-region street routes; these are placement reserves, not inserted cells.',budget_ps=gate['common_clock_contract_ps'],reset=gate['source_reset'],held=['Token final small FF halo relocation must be overlaid and re-audited','Actual CTS topology, cell count, root-to-region routing and arrival/skew are not measured','Exact regenerated kit geometry/PDN and actual PG connectivity','Current native reset/START source/parent joins','No PLACE/CTS/GRT/STA authorization from this PREP'])
out['held']=out['held'][1:]
out['source']='Exact0525 scalar clk graph; frozen candidate8 native rows and actual GEN-snapped macro geometry'
out['fanout_area_model']={
 'local_leaf_design_target':32,
 'local_leaf_buffer_count':sum((x['sink_count']+31)//32 for x in leaves),
 'regional_root_buffer_count':len(leaves),
 'upper_branch_fanout_design_target':8,
 'upper_branch_buffer_count':(len(leaves)+7)//8,
 'primary_entry_buffer_count':1,
 'reserved_regional_buffer_area_um2':len(leaves)*1.62*.27,
 'basis':'Prospective four-tier fanout model: primary -> up to8 regional-root branches -> local32-sink leaf buffers -> FF/SRAM clocks. Count targets are architecture-sizing assumptions, not electrically qualified max fanouts. Exact repeaters/leaf sites and measured delays require normal native CTS.',
}
f=out['fanout_area_model']; f['prospective_buffer_count_before_wire_repeaters']=f['local_leaf_buffer_count']+f['regional_root_buffer_count']+f['upper_branch_buffer_count']+1
f['all_BUFx24_area_before_wire_repeaters_um2']=f['prospective_buffer_count_before_wire_repeaters']*1.62*.27
(R/'clock_model.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k not in ('roots','sinks')},indent=2),flush=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(10,13))
for m in macros.values():
    a,b,c,d=m['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#d4d6db',edgecolor='#555',linewidth=.4))
colors=plt.cm.tab20(np.arange(len(leaves))%20)
for l,col in zip(leaves,colors):
    pts=np.array([sinks[k][:2] for k in l['sink_indices']]);ax.scatter(pts[:,0],pts[:,1],s=.35,color=col)
    x,y=l['xy_um'];ax.scatter(x,y,marker='x',s=28,color='black');ax.text(x+2,y+1,str(l['sink_count']),fontsize=5)
rx,ry=gate['declared_points']['clk'];ax.scatter(rx,ry,s=80,marker='*',color='red',label='One scalar clock entry')
ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',xlabel='um',ylabel='um',title=f'Programme native clock geometry PREP: {len(sm):,} actual sinks / {len(leaves)} regional CTS reserves\nFull pin envelopes <=220um; TT250/FF202.5ps are budgets, actual CTS held')
ax.legend(loc='upper left');fig.tight_layout();fig.savefig(R/'clock_review.png',dpi=160)
