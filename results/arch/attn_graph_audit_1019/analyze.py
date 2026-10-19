import json,collections,math,hashlib,gzip
from pathlib import Path
p=Path(__file__).resolve().parent
cells={};pins={};nets=collections.defaultdict(list);rows=[];pg=[];ports={};units=1000
for line in (p/'graph.tsv').open():
 a=line.rstrip('\n').split('\t');typ=a[0]
 if typ=='CELL': cells[a[1]]={'master':a[2],'orient':a[3],'status':a[4],'bbox':[int(x)/units for x in a[5:9]]}
 elif typ=='PIN':
  xy=[int(x)/units for x in a[-2:]];pins[a[1]]={'dir':a[2],'role':a[3],'net':a[4],'xy':xy};nets[a[4]].append(a[1])
 elif typ=='PORT':
  xy=[(int(a[6])+int(a[8]))/2/units,(int(a[7])+int(a[9]))/2/units];name='PORT:'+a[1];pins[name]={'dir':a[2],'role':a[3],'net':a[4],'xy':xy};nets[a[4]].append(name);ports[name]=pins[name]
 elif typ=='ROW':rows.append(a)
 elif typ.startswith('PG'):pg.append(a)
def inst(pin):return pin.split('/')[0]
def isport(pin):return pin.startswith('PORT:')
def master(pin):return '' if isport(pin) else cells[inst(pin)]['master']
def ff(pin):return master(pin).startswith('DFF')
def transparent(pin):return master(pin).startswith(('BUF','INV','HB'))
def driver(pin):return pins[pin]['dir']==('INPUT' if isport(pin) else 'OUTPUT')
def role(pin):
 if isport(pin):return 'input'
 if ff(pin):return 'reset_ff' if inst(pin).startswith('cpr32') or pin.endswith('/RESETN') else 'ff'
 if master(pin).startswith('TIE'):return 'tie'
 return 'comb'
signal={n:[x for x in v if pins[x]['role'] not in ('POWER','GROUND')] for n,v in nets.items()};drvs={n:[x for x in v if driver(x)] for n,v in signal.items()};loads={n:[x for x in v if not driver(x)] for n,v in signal.items()}
outputs=collections.defaultdict(list);inputs=collections.defaultdict(list)
for x in pins:
 if not isport(x) and pins[x]['role'] not in ('POWER','GROUND'):(outputs if driver(x) else inputs)[inst(x)].append(x)
def endpoints(root):
 todo=list(loads[pins[root]['net']]);seen=set();ends=set()
 while todo:
  q=todo.pop()
  if q in seen:continue
  seen.add(q)
  if transparent(q):
   for o in outputs[inst(q)]:todo.extend(loads[pins[o]['net']])
  else:ends.add(q)
 return ends
census=[]
for net,ds in drvs.items():
 for d in ds:
  if pins[d]['role']=='CLOCK' or (isport(d) and d=='PORT:ck') or transparent(d):continue
  e=endpoints(d);census.append({'driver':d,'role':role(d),'loads':len(e),'endpoints':sorted(e)})
by=collections.defaultdict(list)
for r in census:by[r['role']].append(r)
# Complete DAG propagation: each comb output takes the longest complete wire-only path
# from any FF output. Intra-cell wire is zero; all net edges use actual pin Manhattan distance.
adj=collections.defaultdict(list);indeg=collections.Counter();nodes=set();distance={};origin={};prev={}
for n,ds in drvs.items():
 for d in ds:
  if pins[d]['role'] in ('POWER','GROUND','CLOCK') or d=='PORT:ck':continue
  if ff(d):distance[d]=0;origin[d]=d
  for q in loads[n]:
   if q.endswith('/CLK'):continue
   w=sum(abs(a-b) for a,b in zip(pins[d]['xy'],pins[q]['xy']));adj[d].append((q,w));indeg[q]+=1;nodes.update((d,q))
for i,outs in outputs.items():
 if cells[i]['master'].startswith('DFF'):continue
 for q in inputs[i]:
  if pins[q]['role'] in ('POWER','GROUND','CLOCK'):continue
  for o in outs:adj[q].append((o,0));indeg[o]+=1;nodes.update((q,o))
queue=collections.deque(x for x in nodes if not indeg[x]);visited=0
while queue:
 x=queue.popleft();visited+=1
 for y,w in adj[x]:
  if x in distance and distance.get(y,-1)<distance[x]+w:distance[y]=distance[x]+w;origin[y]=origin[x];prev[y]=x
  indeg[y]-=1
  if not indeg[y]:queue.append(y)
stages=sorted([{'endpoint':x,'origin':origin[x],'wire_um':v} for x,v in distance.items() if ff(x) and not driver(x) and not x.endswith('/CLK')],key=lambda x:-x['wire_um'])
for s in stages[:20]:
 path=[];cur=s['endpoint']
 while cur in prev:path.append(cur);cur=prev[cur]
 s['path']=list(reversed(path+[cur]))
# Fixed-face ancestry without assuming direct pin regs.
def face(x):
 a,b=pins[x]['xy'];return min({'W':abs(a),'E':abs(216-a),'S':abs(b),'N':abs(216-b)},key=lambda k:{'W':abs(a),'E':abs(216-a),'S':abs(b),'N':abs(216-b)}[k])
def boundary(root,reverse=False):
 todo=[(root,0)];seen=set();found=set();bad=[]
 while todo:
  x,depth=todo.pop()
  if x in seen:continue
  seen.add(x)
  if ff(x):found.add(inst(x));continue
  if isport(x) and x!=root:bad.append(x);continue
  if reverse:
   ns=drvs[pins[x]['net']] if not driver(x) else inputs[inst(x)]
  else:ns=loads[pins[x]['net']] if driver(x) else outputs[inst(x)]
  if not ns:bad.append(x)
  todo.extend((y,depth+1) for y in ns)
 return {'ff':sorted(found),'dead_or_other_ports':sorted(bad),'visited':len(seen)}
bounds={x:{'face':face(x),'direction':pins[x]['dir'],**boundary(x,pins[x]['dir']=='OUTPUT')} for x in ports if pins[x]['role'] not in ('POWER','GROUND') and x!='PORT:ck'}
own=collections.defaultdict(set)
for x,b in bounds.items():
 for f in b['ff']:own[f].add(b['face'])
reset=[]
for i,c in cells.items():
 if i.startswith('cpr32_'):
  ds=outputs[i];sink=[]
  for d in ds:sink.extend(endpoints(d))
  reset.append({'cell':i,**c,'signal_inputs':{q:pins[q] for q in inputs[i] if pins[q]['role'] not in ('POWER','GROUND')},'logical_loads':len(set(sink)),'endpoints':sorted(set(sink))})
summary={'cells':len(cells),'ff':sum(c['master'].startswith('DFF') for c in cells.values()),'signal_ports':len(bounds)+1,'signal_pin_partitions':len(signal),'driver_role_counts':{k:len(v) for k,v in by.items()},'driver_role_max':{k:max(x['loads'] for x in v) for k,v in by.items()},'over32':sum(r['loads']>32 for r in census),'multiple_driver_signal_nets':[n for n,v in drvs.items() if len(v)>1],'stage_graph_nodes':len(nodes),'stage_graph_visited':visited,'stage_graph_cycles':len(nodes)-visited,'complete_ff_stage_count':len(stages),'stage_wire_max_um':stages[0]['wire_um'] if stages else None,'stage_wire_over405':sum(x['wire_um']>405 for x in stages),'top_stages':stages[:20],'cross_face_boundary_ff':{k:sorted(v) for k,v in own.items() if len(v)>1},'boundary_dead_port_count':sum(bool(b['dead_or_other_ports']) for b in bounds.values()),'reset_copies':reset,'pg_records_count':len(pg),'pg_native_connectivity':'UNQUALIFIED: assigned net and metal rectangles are not via/access connectivity proof','native_clock':'NULL: no CTS, ideal clock only','rows':len(rows)}
for name,obj in [('summary.json',summary),('census.json.gz',census),('boundary.json.gz',bounds),('stages.json.gz',stages)]:
 if name.endswith('.gz'):
  with gzip.open(p/name,'wt') as f:json.dump(obj,f)
 else:(p/name).write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('top_stages','reset_copies','cross_face_boundary_ff')},indent=2))
# Additional auditable partitions and physical legality, without timing exemptions.
reset=[r for r in reset if r['master'].startswith('DFF')]
for r in reset:
 anc=r['cell'].split('_')[1];r['declared_same_edge_ancestor']=anc;r['ancestor_cell']=cells.get(anc)
 r['ancestor_inputs']={q:pins[q] for q in inputs[anc] if pins[q]['role'] not in ('POWER','GROUND')}
 r['D_CLK_RESETN_SETN_identical_to_ancestor']={k:pins[r['cell']+'/'+k]['net']==pins[anc+'/'+k]['net'] for k in ('D','CLK','RESETN','SETN')}
stage_types=collections.defaultdict(list)
for s in stages:stage_types['async' if s['endpoint'].endswith(('/RESETN','/SETN')) else 'data'].append(s)
rowbuckets=collections.defaultdict(list);offgrid=[];outside=[]
for i,c in cells.items():
 x,y,X,Y=c['bbox'];rowbuckets[round(y,6)].append((x,X,i))
 if abs((Y-y)-.27)>1e-6 or abs((y-2.16)/.27-round((y-2.16)/.27))>1e-6 or abs(x/.054-round(x/.054))>1e-6:offgrid.append(i)
 if min(x,y)<2.16-1e-6 or max(X,Y)>213.84+1e-6:outside.append(i)
overlaps=[]
for y,items in rowbuckets.items():
 items.sort();right=-1;last=None
 for x,X,i in items:
  if x<right-1e-6:overlaps.append([last,i,y])
  if X>right:right=X;last=i
# All ordinary public data inputs must reach first FF D without a combinational gate,
# allowing buffers/inverters only to expose any remaining first-contact exception.
direct_ex=[]
for x,b in bounds.items():
 es=endpoints(x) if pins[x]['dir']=='INPUT' else None
 if es is not None:
  bad=[e for e in es if not(ff(e) and e.endswith('/D'))]
  if bad:direct_ex.append({'port':x,'exceptions':bad})
# Preserve exact path cell equations and read-side port bindings.
critical=['c14180','cprl30','cprc44','cprc46','cprc48','cpro49','c2161','c2162','c2167','c2168','c2202','c2203','c2343','c30776','c29959','c23566','c9530','c9533','cpo216_ff']
crit={i:{'cell':cells[i],'pins':{x:pins[x] for x in inputs[i]+outputs[i]}} for i in critical}
# Clock and PG are reported separately; assigned PG nets do not establish physical contacts.
pgcounts=collections.Counter(a[0] for a in pg);pgassigned=collections.Counter((v['role'],v['net']) for v in pins.values() if v['role'] in ('POWER','GROUND'))
summary.update({'reset_copies':reset,'reset_copy_count':len(reset),'stage_wire_by_type':{k:{'count':len(v),'max_um':max(x['wire_um'] for x in v),'over405':sum(x['wire_um']>405 for x in v)} for k,v in stage_types.items()},'legal_grid_offenders':offgrid,'core_outside':outside,'row_overlap_pairs':overlaps,'direct_input_first_contact_exceptions':direct_ex,'pg_record_types':dict(pgcounts),'pg_pin_assigned_counts':{str(k):v for k,v in pgassigned.items()},'actual_clock_port':ports.get('PORT:ck'),'boundary_dead_port_explanation':'A backwards output cone may terminate at a tie; see boundary ledger, no exemption inferred.'})
(p/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(p/'critical_cells.json').write_text(json.dumps(crit,indent=2)+'\n')
print('ADDITIONAL',json.dumps({k:summary[k] for k in ('reset_copy_count','stage_wire_by_type','legal_grid_offenders','core_outside','row_overlap_pairs','pg_record_types','pg_pin_assigned_counts','actual_clock_port')},indent=2))
# ROOT scope: 405um existing reach rule applies to individual logical connections.
# A complete FF-stage wire sum is a timing diagnostic, not a new reach rejection.
logical=[]
for r in census:
 d=r['driver']
 for e in r['endpoints']:
  logical.append({'driver':d,'endpoint':e,'role':r['role'],'manhattan_um':sum(abs(x-y) for x,y in zip(pins[d]['xy'],pins[e]['xy']))})
logical.sort(key=lambda r:-r['manhattan_um'])
summary['individual_logical_reach']={'metric':'Manhattan between actual native logical driver and logical endpoint pin, BUF/INV/HB transparent; placement geometry, not routed wire','max_um':logical[0]['manhattan_um'],'over405':sum(r['manhattan_um']>405 for r in logical),'top20':logical[:20],'by_role':{k:{'max_um':max((r['manhattan_um'] for r in logical if r['role']==k),default=0),'over405':sum(r['manhattan_um']>405 for r in logical if r['role']==k)} for k in by}}
summary['complete_stage_wire_interpretation']='TIMING DIAGNOSTIC ONLY, not a separate405um reach rejection'
summary['unconsumed_input_count']=sum(v['direction']=='INPUT' and not v['ff'] for v in bounds.values())
summary['constant_output_without_last_ff_count']=sum(v['direction']=='OUTPUT' and not v['ff'] for v in bounds.values())
(p/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(p/'logical_reach.json.gz','wt') as f:json.dump(logical,f)
print('INDIVIDUAL_LOGICAL_REACH',json.dumps(summary['individual_logical_reach'],indent=2))
