exec(open('results/arch/hbm_col8_parent_1021/geometry_scripts/export.py').read().replace("print(json.dumps(result['reach_audit'],indent=2))",''))
import numpy as np
bands=[a for a in rect if a['kind']=='FF_band'];hard=[a for a in rect if a['kind'] in ('pair','SRAM')]
key=lambda a:tuple(round(float(x),4) for x in a)
lookup={key((a['x_um']+a['width_um']/2,a['y_um']+a['height_um']/2)):i for i,a in enumerate(bands)}
edges=[]
for c in checks:
 a,b=c['from_um'],c['to_um'];edges.append((lookup.get(key(a)),lookup.get(key(b)),np.array(a),np.array(b),c['net']))
pos=np.array([[a['x_um']+a['width_um']/2,a['y_um']+a['height_um']/2] for a in bands]);initial=pos.copy()
g=np.arange(10.8,900,5.4);xx,yy=np.meshgrid(g,g);grid=np.array([xx.ravel(),yy.ravel()]).T
for iteration in range(14):
 for i in range(len(bands)):
  a=bands[i];w,h=a['width_um'],a['height_um'];radius=(w+h)/2
  cand=grid.copy();ok=np.ones(len(cand),bool)
  for b in hard:
   ok &= ~((cand[:,0]+w/2>b['x_um']-5.4)&(cand[:,0]-w/2<b['x_um']+b['width_um']+5.4)&(cand[:,1]+h/2>b['y_um']-5.4)&(cand[:,1]-h/2<b['y_um']+b['height_um']+5.4))
  for j,b in enumerate(bands):
   if j==i:continue
   ok &= ~((np.abs(cand[:,0]-pos[j,0])<(w+b['width_um'])/2+1.08)&(np.abs(cand[:,1]-pos[j,1])<(h+b['height_um'])/2+1.08))
  cand=cand[ok];ends=[]
  for ia,ib,pa,pb,n in edges:
   if ia==i:ends.append(pos[ib] if ib is not None else pb)
   if ib==i:ends.append(pos[ia] if ia is not None else pa)
  if not ends:score=np.zeros(len(cand))
  else:
   ends=np.array(ends);u=ends[:,0]+ends[:,1];v=ends[:,0]-ends[:,1];cu=cand[:,0]+cand[:,1];cv=cand[:,0]-cand[:,1]
   score=np.maximum.reduce([cu-u.min(),u.max()-cu,cv-v.min(),v.max()-cv])+radius
  cost=np.maximum(score-405,0)*10000+np.abs(cand-initial[i]).sum(axis=1)*.01+score*.1
  pos[i]=cand[np.argmin(cost)]
for i,a in enumerate(bands):a['x_um']=round(pos[i,0]-a['width_um']/2,4);a['y_um']=round(pos[i,1]-a['height_um']/2,4)
newchecks=[]
for ia,ib,pa,pb,n in edges:
 aa=pos[ia] if ia is not None else pa;bb=pos[ib] if ib is not None else pb
 distance=float(np.abs(aa-bb).sum());rad=sum((bands[j]['width_um']+bands[j]['height_um'])/2 for j in [ia,ib] if j is not None)
 newchecks.append(dict(net=n,from_um=aa.tolist(),to_um=bb.tolist(),manhattan_center_um=round(distance,4),band_corner_upper_bound_um=round(distance+rad,4)))
bad=sorted([c for c in newchecks if c['band_corner_upper_bound_um']>405],key=lambda c:-c['band_corner_upper_bound_um'])
result['reach_audit']=dict(kind='Exact LEF pin midpoint and pessimistic full FF band corner Manhattan bounds; not detailed route or CTS proof',net_count=len(newchecks),max_center_um=max(c['manhattan_center_um'] for c in newchecks),max_band_corner_um=max(c['band_corner_upper_bound_um'] for c in newchecks),violations=bad,hard_macro_halo_um=5.4)
result['next']='Compose actual full-count placement and qualify clock/reset/timing. R3 remains a stand-in.'
(out/'column_geometry.json').write_text(json.dumps(result,indent=2)+'\n');(out/'column_geometry_paths.json').write_text(json.dumps(newchecks,indent=2)+'\n')
print('violations',len(bad),'max',result['reach_audit']['max_band_corner_um']);print(json.dumps(bad[:3],indent=2));print([(a['name'],pos[i].tolist()) for i,a in enumerate(bands)])
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 940 950">','<rect width="907.2" height="907.2" fill="white" stroke="black"/>']
for a in rect:
 color={'pair':'#9cbde0','SRAM':'#e1c88f','FF_band':'#9dc79d','control_reserve':'#d7b2ce'}[a['kind']];x,y,w,h=[a[k] for k in ['x_um','y_um','width_um','height_um']];svg.append(f'<rect x="{x}" y="{907.2-y-h}" width="{w}" height="{h}" fill="{color}" stroke="black" stroke-width="0.5"/><text x="{x}" y="{907.2-y-h+8}" font-size="7">{a["name"]}</text>')
svg.append('<text x="0" y="930" font-size="12">One column, 907.2 x 907.2 um. Diagnostic geometry. R3 is a stand-in.</text></svg>');(out/'column_geometry.svg').write_text('\n'.join(svg))
