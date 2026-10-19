"""Native placement bounds, without clock/timing/routing qualification."""
import json,math,collections,heapq,hashlib,gzip
from pathlib import Path
p=Path(__file__).resolve().parent
x=json.loads((p/'placed_geometry.json').read_text());f=json.loads((p/'floorplan.json').read_text());cells=x['cells'];ports=x['ports']
def seq(c):return not c['block'] and any(z in c['pins'] for z in ('CLK','CK'))
def xyport(n):
 rs=ports[n]['boxes'];return [sum((a[0]+a[2])/2 for a in rs)/len(rs),sum((a[1]+a[3])/2 for a in rs)/len(rs)]
def loc(t):return cells[t[0]]['pins'][t[1]]
def l1(a,b):return sum(abs(u-v) for u,v in zip(a,b))
def overlap(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
macros={n:c for n,c in cells.items() if c['block']};std={n:c for n,c in cells.items() if not c['block']};ffs={n:c for n,c in std.items() if seq(c)}
rows=x['rows'];band=[21.6,226.8,712.8,231.66]
macroover=[(n,m,overlap(c['bbox'],d['bbox'])) for n,c in std.items() for m,d in macros.items() if overlap(c['bbox'],d['bbox'])>1e-8]
outside=[n for n,c in std.items() if c['bbox'][0]<band[0]-1e-6 or c['bbox'][1]<band[1]-1e-6 or c['bbox'][2]>band[2]+1e-6 or c['bbox'][3]>band[3]+1e-6]
# Independent sweep detects actual standard-cell rectangle overlaps.
active=[];std_over=[]
for n,c in sorted(std.items(),key=lambda v:v[1]['bbox'][0]):
 a=c['bbox'];active=[v for v in active if v[1][2]>a[0]+1e-7]
 for m,b in active:
  z=overlap(a,b)
  if z>1e-8:std_over.append([n,m,z])
 active.append((n,a))
legs=[];net_in={};cell_inputs=collections.defaultdict(list);cell_outputs=collections.defaultdict(list)
for name,n in x['nets'].items():
 drivers=[{'endpoint':t,'xy':loc(t),'kind':'cell'} for t in n['cells'] if t[2]=='OUTPUT']+[{'endpoint':[z],'xy':xyport(z),'kind':'port'} for z in n['ports'] if ports[z]['direction']=='INPUT']
 sinks=[{'endpoint':t,'xy':loc(t),'kind':'cell'} for t in n['cells'] if t[2]=='INPUT']+[{'endpoint':[z],'xy':xyport(z),'kind':'port'} for z in n['ports'] if ports[z]['direction']=='OUTPUT']
 clock=any(t[1] in ('CLK','CK','clk','ck') for t in n['cells'])
 constant=any(t[0] in std and cells[t[0]]['master'].startswith(('TIEHI','TIELO')) for t in n['cells'] if t[2]=='OUTPUT')
 reset=any(t[1] in ('RESETN','SETN','RN','SN','rst_n','reset_n') for t in n['cells'] if t[2]=='INPUT')
 role='clock' if clock else 'constant' if constant else 'reset' if reset else 'data'
 for d in drivers:
  for s in sinks:legs.append({'net':name,'role':role,'driver':d,'sink':s,'manhattan_um':l1(d['xy'],s['xy'])})
 if len(drivers)==1:
  net_in[name]={'driver':drivers[0],'role':role}
 for t in n['cells']:
  if t[2]=='INPUT':cell_inputs[t[0]].append((name,t))
  elif t[2]=='OUTPUT':cell_outputs[t[0]].append((name,t))
# Longest source-to-state/boundary path upper envelope over all combinational input/output arcs.
# Wire lengths are Manhattan lower bounds; no routed/electrical claim follows.
comb={n for n,c in std.items() if not seq(c) and not c['master'].startswith(('TIEHI','TIELO'))}
indeg={n:0 for n in comb};nexts=collections.defaultdict(list)
for c in comb:
 deps={net_in[n]['driver']['endpoint'][0] for n,t in cell_inputs[c] if n in net_in and net_in[n]['driver']['kind']=='cell' and net_in[n]['driver']['endpoint'][0] in comb}
 indeg[c]=len(deps)
 for d in deps:nexts[d].append(c)
q=collections.deque(n for n,v in indeg.items() if not v);order=[]
while q:
 c=q.popleft();order.append(c)
 for n in nexts[c]:
  indeg[n]-=1
  if not indeg[n]:q.append(n)
arr={};stage=[]
def arrival(n,xy):
 if n not in net_in:return None
 d=net_in[n]['driver'];role=net_in[n]['role']
 if role in ('clock','constant','reset'):return None
 key=tuple(d['endpoint'][:2]);a=arr.get(key)
 if d['kind']=='port' or (d['kind']=='cell' and (d['endpoint'][0] not in comb)):
  a={'distance':0.,'source':d['endpoint'],'path':[]}
 if a is None:return None
 return {'distance':a['distance']+l1(d['xy'],xy),'source':a['source'],'path':a['path']+[n]}
for c in order:
 incoming=[]
 for n,t in cell_inputs[c]:
  a=arrival(n,loc(t))
  if a:incoming.append((a,loc(t)))
 for n,t in cell_outputs[c]:
  if incoming:
   a,px=max(incoming,key=lambda v:v[0]['distance']+l1(v[1],loc(t)));arr[tuple(t[:2])]={'distance':a['distance']+l1(px,loc(t)),'source':a['source'],'path':a['path']}
for c in cells:
 if c in comb:continue
 for n,t in cell_inputs[c]:
  if t[1] in ('CLK','CK','clk','ck','RESETN','SETN','rst_n','reset_n'):continue
  a=arrival(n,loc(t))
  if a:stage.append({**a,'sink':t[:2]})
for n,v in x['nets'].items():
 for z in v['ports']:
  if ports[z]['direction']=='OUTPUT':
   a=arrival(n,xyport(z))
   if a:stage.append({**a,'sink':[z]})
byrole={role:sorted([v for v in legs if v['role']==role],key=lambda v:-v['manhattan_um']) for role in ('data','reset','constant','clock')}
centroid=[sum((c['bbox'][k]+c['bbox'][k+2])/2 for c in ffs.values())/len(ffs) for k in (0,1)]
boundary={e['inst'] for z in f['ports'] for e in z['endpoints'] if e['is_ff']}
assert len(boundary)==645 and len(ffs)==3420 and len(macros)==5
facelegs=[v for v in legs if v['driver']['kind']=='port' or v['sink']['kind']=='port']
boundary_part=[{'inst':n,'box_um':cells[n]['bbox'],'ports':[z['port'] for z in f['ports'] if any(e['inst']==n for e in z['endpoints'])]} for n in sorted(boundary)]
area=sum((c['bbox'][2]-c['bbox'][0])*(c['bbox'][3]-c['bbox'][1]) for c in std.values());cap=(band[2]-band[0])*(band[3]-band[1])
metrics={'schema':'opentallas.ahub.fixed_face_geometry.v1','qualified':False,'source_sha256':f['source_native_sha256'],'std_count':len(std),'ff_count':len(ffs),'boundary_ff_count':len(boundary),'clock_sinks':3425,'macro_count':len(macros),'std_area_um2':area,'band_um':band,'legal_row_count':len(rows),'row_area_um2':sum((a[2]-a[0])*(a[3]-a[1]) for a in rows),'band_area_um2':cap,'utilization_percent':area/cap*100,'independent_macro_overlaps':macroover,'independent_std_overlaps':std_over,'outside_band':outside,'graph_receipt':json.loads((p/'native_graph_receipt.json').read_text()),'face_counts':f['face_counts'],'face_density_per_um':f['face_density_per_um'],'clock_entry_um':xyport('ck'),'ff_centroid_um':centroid,'clock_entry_centroid_manhattan_um':l1(xyport('ck'),centroid),'clock_regional_root_proposal_um':[367.2,229.23],'max_manhattan_by_role_um':{k:max((z['manhattan_um'] for z in v),default=0) for k,v in byrole.items()},'over405_by_role':{k:sum(z['manhattan_um']>405 for z in v) for k,v in byrole.items()},'maximum_face_leg_manhattan_um':max(v['manhattan_um'] for v in facelegs if v['role']=='data'),'max_stage_manhattan_sum_um':max(v['distance'] for v in stage),'stage_over405_count':sum(v['distance']>405 for v in stage),'combinational_cycle_cell_count':len(comb)-len(order),'open':['All Manhattan figures are ideal lower bounds, not routed lengths. Macro detours and PG obstacles can increase wire lengths.','No CTS, native loaded TT/FF timing, spread/launch/capture, PDN or hard-child power connection qualification.','Production POR/admission and functional fault propagation remain separate open obligations.']}
(p/'metrics.json').write_text(json.dumps(metrics,indent=2));(p/'boundary_ownership.json').write_text(json.dumps(boundary_part,indent=2))
with gzip.open(p/'reach_census.json.gz','wt') as z:json.dump({'legs':legs,'stages':stage},z)
print(json.dumps(metrics,indent=2))
# Visualization is an artifact, never a geometry substitute.
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(13,9))
for n,c in macros.items():
 a,b,cx,d=c['bbox'];ax.add_patch(Rectangle((a,b),cx-a,d-b,facecolor='#d9e8ef',edgecolor='#355968'));ax.text((a+cx)/2,(b+d)/2,n+'\nR0',ha='center',va='center',fontsize=8)
a,b,c,d=band;ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#61a96c',alpha=.8))
for n,z in std.items():
 a,b,c,d=z['bbox'];ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#882d2d' if n in boundary else '#28639c',edgecolor='none'))
for n in ports:
 xx,yy=xyport(n);ax.plot(xx,yy,'.',ms=2,color='#222222')
for role,color in [('data','#c12d2d'),('reset','#a26b00')]:
 for v in byrole[role][:3]:
  a=v['driver']['xy'];b=v['sink']['xy'];ax.plot([a[0],b[0]],[a[1],b[1]],'--',color=color,alpha=.6,lw=1)
clk=xyport('ck');ax.plot(*clk,'*',color='#f08a00',ms=12);ax.annotate('Clock entry; native phase unmeasured',clk,(390,560),arrowprops={'arrowstyle':'->'},fontsize=8)
ax.add_patch(Rectangle((0,0),734.4,540,fill=False,lw=2));ax.text(367.2,211,f'Single legal band; {area:.2f} µm² / {cap:.2f} µm² = {area/cap*100:.2f}%\n645 dedicated boundary FF; full restored native graph',ha='center',fontsize=9)
ax.set(xlim=(-20,755),ylim=(-20,580),aspect='equal',xlabel='µm',ylabel='µm');ax.set_title('AHUB revised source: exact native placement and reach preflight\nGeometry only; no CTS / routing / PG / timing qualification');fig.tight_layout();fig.savefig(p/'placement.png',dpi=160)
