"""Exact-native-graph constructive packing and cut/reach planning, not P&R.

No GPL/CTS/route is run. Every existing cell gets an analytic legal row slot.
All direct endpoints are bounded by full standard-cell boxes; macro and top
terminals use actual native geometry. BUF/INV transparency uses actual Liberty.
"""
import csv, json, math, heapq, collections, argparse, hashlib, re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--roles',type=Path,required=True);a=p.parse_args();d=a.directory
B=(2.16,259.2,473.04,291.6);SITE=.054;RH=.270
roles=json.loads(a.roles.read_text())['roles'];layout=json.loads((d/'layout.json').read_text())
cells={r['instance']:r for r in csv.DictReader((d/'ot_lep_source_mapped_cells.tsv').open(),delimiter='\t')}
master_counts=collections.Counter(r['master'] for r in cells.values())
for r in cells.values():
 r['w']=float(r['x1_um'])-float(r['x0_um']);r['h']=float(r['y1_um'])-float(r['y0_um'])
 if abs(r['h']-RH)>1e-6 or abs(r['w']/SITE-round(r['w']/SITE))>1e-5:raise ValueError(('unsupported native row/site cell',r))
 if r['master'] not in roles:raise ValueError(('unknown actual Liberty master',r['master']))
macro={}
for r in csv.DictReader((d/'macro_terminals.tsv').open(),delimiter='\t'):
 macro[(r['instance'],r['pin'])]=tuple(float(r[k]) for k in ['x0_um','y0_um','x1_um','y1_um'])
ports={r[0]:tuple(r[2:]) for r in layout['pins']}
parent={}
def find(n):
 parent.setdefault(n,n)
 while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
 return n
def union(x,y):
 x,y=find(x),find(y)
 if x!=y:parent[y]=x
rows=list(csv.DictReader((d/'native_graph.tsv').open(),delimiter='\t'));bycell=collections.defaultdict(dict);const=set();transparent=set();errors=[]
for r in rows:
 if r['role'] in ['POWER','GROUND']:continue
 if r['kind']=='port':
  r['clock']=r['pin']=='clk';continue
 role=roles.get(r['master'])
 if role is None:errors.append(('unknown master',r['master']));continue
 pr=role['pins'].get(r['pin']) or role['pins'].get(re.sub(r'\[\d+\]$','',r['pin']))
 if pr is None:errors.append(('unknown pin',r['master'],r['pin']));continue
 r['clock']=pr['clock']
 if not r['clock']:bycell[r['instance']][r['pin']]=r['net']
 if pr['direction']=='output' and pr['function'] in ['0','1',"1'b0","1'b1"]:const.add(r['net'])
# Master lookup avoids a quadratic scan.
masters={r['instance']:r['master'] for r in rows if r['kind']=='cell'}
for n,conn in bycell.items():
 role=roles[masters[n]]
 def pr(x):return role['pins'].get(x) or role['pins'][re.sub(r'\[\d+\]$','',x)]
 ins=[x for x in conn if pr(x)['direction']=='input'];outs=[x for x in conn if pr(x)['direction']=='output']
 if not role['sequential'] and len(ins)==len(outs)==1:
  fn=(pr(outs[0])['function'] or '').replace(' ','').replace('(','').replace(')','')
  if fn in [ins[0],'!'+ins[0],ins[0]+"'"]:
   union(conn[ins[0]],conn[outs[0]]);transparent.add(n)
const={find(x) for x in const}
if errors:raise ValueError(errors[:8])
nets=collections.defaultdict(lambda:{'cells':set(),'anchors':[],'drivers':[],'terms':[]})
for r in rows:
 if r['role'] in ['POWER','GROUND'] or r.get('clock'):continue
 net=find(r['net'])
 if net in const or r['instance'] in transparent:continue
 q=nets[net];n=r['instance'];pin=r['pin'];kind=r['kind']
 if kind=='port':
  if pin=='rst_n':pass # Reset remains a real dynamic data endpoint.
  if pin not in ports:raise ValueError(('missing native port geometry',pin))
  box=ports[pin];q['anchors'].append(box);ep=('port',pin,box)
  if r['direction']=='INPUT':q['drivers'].append(ep)
 elif n in cells:
  q['cells'].add(n);ep=('cell',n,pin)
  if r['direction']=='OUTPUT':q['drivers'].append(ep)
 else:
  if (n,pin) not in macro:raise ValueError(('missing native macro terminal',n,pin))
  box=macro[n,pin];q['anchors'].append(box);ep=('macro',n+'/'+pin,box)
  if r['direction']=='OUTPUT':q['drivers'].append(ep)
 q['terms'].append(ep)
nets={k:v for k,v in nets.items() if v['terms']}
for k,q in nets.items():
 if len(q['drivers'])!=1:raise ValueError(('not one native driver',k,q['drivers']))
incident=collections.defaultdict(list)
for k,q in nets.items():
 for n in q['cells']:incident[n].append(k)
hard={n:[B[0]+cells[n]['w']/2,B[2]-cells[n]['w']/2] for n in cells}
refusals=[]
for k,q in nets.items():
 if not q['anchors']:continue
 bs=q['anchors'];ax0=min(b[0] for b in bs);ax1=max(b[2] for b in bs)
 height=max([B[3]]+[b[3] for b in bs])-min([B[1]]+[b[1] for b in bs]);span=405-height
 if ax1-ax0>span+1e-6:refusals.append({'net':k,'anchors':bs,'reason':'no full-band-y envelope fits fixed terminals'})
 for n in q['cells']:
  hard[n][0]=max(hard[n][0],ax1-span+cells[n]['w']/2)
  hard[n][1]=min(hard[n][1],ax0+span-cells[n]['w']/2)
for n,(lo,hi) in hard.items():
 if lo>hi:refusals.append({'cell':n,'interval':[lo,hi],'reason':'incompatible fixed-terminal full-band envelope'})
(d/'fixed_interval_refusals.json').write_text(json.dumps(refusals,indent=2)+'\n')
if refusals:raise ValueError(('fixed-terminal full-band planning refusal',len(refusals),refusals[:2]))
x={n:(hard[n][0]+hard[n][1])/2 for n in cells}
for iteration in range(35):
 means={k:(sum(x[n] for n in q['cells'])+sum((b[0]+b[2])/2 for b in q['anchors']))/(len(q['cells'])+len(q['anchors'])) for k,q in nets.items()}
 x={n:max(hard[n][0],min(hard[n][1],.25*x[n]+.75*(sum(means[k] for k in incident[n])/len(incident[n]) if incident[n] else x[n]))) for n in cells}
# Constructive native-site legal packing, not a placement-engine result.
rowcells=[[] for _ in range(120)];heap=[(0.,i) for i in range(120)];heapq.heapify(heap)
for n in sorted(cells,key=lambda n:(x[n],n)):
 w,i=heapq.heappop(heap);rowcells[i].append(n);heapq.heappush(heap,(w+cells[n]['w'],i))
boxes={};maxrow=0
for i,ns in enumerate(rowcells):
 total=sum(cells[n]['w'] for n in ns);maxrow=max(maxrow,total)
 if total>B[2]-B[0]+1e-6:raise ValueError(('row capacity',i,total))
 pos={};end=B[0]
 for n in ns:
  desired=round((x[n]-cells[n]['w']/2)/SITE)*SITE
  pos[n]=max(end,desired,math.ceil((hard[n][0]-cells[n]['w']/2)/SITE-1e-7)*SITE);end=pos[n]+cells[n]['w']
 end=B[2]
 for n in reversed(ns):pos[n]=min(pos[n],end-cells[n]['w'],math.floor((hard[n][1]-cells[n]['w']/2)/SITE+1e-7)*SITE);end=pos[n]
 for n in ns:
  if pos[n]<B[0]-1e-5 or pos[n]+cells[n]['w']/2<hard[n][0]-1e-5:raise ValueError(('packing conflicts with fixed-terminal bound',n,pos[n],hard[n]))
  boxes[n]=(pos[n],B[1]+i*RH,pos[n]+cells[n]['w'],B[1]+(i+1)*RH)
netboxes={};bad=[];maxspan=0
for k,q in nets.items():
 bs=list(q['anchors'])+[boxes[n] for n in q['cells']]
 bb=(min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs))
 span=bb[2]-bb[0]+bb[3]-bb[1];maxspan=max(maxspan,span);netboxes[k]=bb
 if span>405:bad.append({'net':k,'bbox':bb,'upper_um':span,'drivers':q['drivers'],'endpoints':q['terms']})
# Actual native routing tracks. Conservatively block every macro on M2..M5;
# discard M2 throughout the logic band for local PG rails, and reserve all top
# M5 PG columns with24nm spacing on both vertical layers. Apply actual ORFS25%
# global capacity reduction. This remains a planning cut, not a routed proof.
tracks={}
for line in (d/'tracks.tsv').read_text().splitlines():
 layer,direction,xs,ys=line.split('\t');tracks[layer]=(direction,[int(z)/1000 for z in xs.split(',') if z],[int(z)/1000 for z in ys.split(',') if z])
# DB units are checked against native grid geometry; ASAP7 uses1000DBU/um.
if not tracks['M3'][1] or abs(tracks['M3'][1][1]-tracks['M3'][1][0]-.036)>1e-5:raise ValueError('native track DBU/pitch mismatch')
macros=[b[2:] for b in layout['blocks']];pg=layout['pg'];cuts=[]
def available(layer,axis,cut):
 vals=tracks[layer][1 if axis=='y' else 2];lo,hi=(B[0],B[2]) if axis=='y' else (2.16,559.44);num=0
 for v in vals:
  if not lo<=v<=hi:continue
  if any((b[0]<=v<=b[2] and b[1]<=cut<=b[3]) if axis=='y' else (b[0]<=cut<=b[2] and b[1]<=v<=b[3]) for b in macros):continue
  if axis=='x' and layer=='M2' and B[1]<=v<=B[3]:continue
  if axis=='y' and any(p[1]=='M5' and p[2]-.024<=v<=p[4]+.024 and p[3]<=cut<=p[5] for p in pg):continue
  num+=1
 return num
for axis,locations,layers in [('y',[B[1]-.001,B[3]+.001],['M3','M5']),('x',[2.16+(473.04-2.16)*i/20 for i in range(1,20)],['M2','M4'])]:
 for cut in locations:
  demand=sum((bb[1]<cut<bb[3]) if axis=='y' else (bb[0]<cut<bb[2]) for bb in netboxes.values())
  cap={l:available(l,axis,cut) for l in layers};effective=math.floor(sum(cap.values())*.75)
  cuts.append({'axis':axis,'coordinate_um':cut,'unique_dynamic_net_crossings':demand,'native_tracks_after_explicit_obstacles':cap,'after_actual_25percent_reduction':effective,'demand_over_capacity':demand/max(effective,1)})
area=sum(float(c['area_um2']) for c in cells.values());ff=sum(1 for c in cells.values() if roles[c['master']]['sequential'])
summary={'schema':'opentallas.lep_native_constructive_planning.v1','native_cells':len(cells),'native_sequential_cells':ff,'native_masters':dict(master_counts),'native_area_um2':area,'band':B,'density':area/((B[2]-B[0])*(B[3]-B[1])),'rows':120,'site_um':SITE,'row_height_um':RH,'max_packed_row_width_um':maxrow,'all_cells_packed_without_overlap':True,'dynamic_roots':len(nets),'actual_library_transparent_cells':len(transparent),'effective_endpoint_bbox_max_um':maxspan,'effective_endpoint_bbox_over405':len(bad),'cuts':cuts,'qualification':False,'limits':['Analytic legal packing; native placement is not run','Endpoint bbox is a constructive planning upper bound, not routed wire length','Clock CTS/TT/FF spread not measured','PG binding is audited separately; unplaced standard pin-metal contact not qualified','Timing setup/hold and congestion require approved gate']}
(d/'packing_summary.json').write_text(json.dumps(summary,indent=2)+'\n');(d/'packing_over405.json').write_text(json.dumps(bad,indent=2)+'\n')
with (d/'packed_cells.tsv').open('w') as f:
 f.write('instance\tmaster\tx0_um\ty0_um\tx1_um\ty1_um\n')
 for n,b in boxes.items():f.write('\t'.join([n,cells[n]['master']]+[str(z) for z in b])+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['native_masters','cuts']},indent=2));print('worst_cut_ratio',max(c['demand_over_capacity'] for c in cuts))
