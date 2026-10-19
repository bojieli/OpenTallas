import collections,json,math,gzip,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
for stage in ['3_2_place_iop.odb','5_1_grt.odb']:
 cells={};pins={};nets=collections.defaultdict(set);units=1000;die=None;pg=[]
 for line in (p/(stage+'.tsv')).open():
  a=line.rstrip('\n').split('\t')
  if a[0]=='META' and a[1]=='units':units=int(a[2])
  if a[0]=='META' and a[1]=='die':die=[int(x)/units for x in a[2:]]
  if a[0]=='CELL':cells[a[1]]={'master':a[2],'bbox':[int(x)/units for x in a[5:9]]}
  if a[0]=='PIN':pins[a[1]]={'dir':a[2],'role':a[3],'net':a[4],'xy':[int(x)/units for x in a[-2:]]};nets[a[4]].add(a[1])
  if a[0]=='PORT':
   n='PORT:'+a[1];pins[n]={'dir':a[2],'role':a[3],'net':a[4],'xy':[(int(a[6])+int(a[8]))/2/units,(int(a[7])+int(a[9]))/2/units]};nets[a[4]].add(n)
  if a[0].startswith('PG'):pg.append(a)
 def inst(q):return q.rsplit('/',1)[0]
 def port(q):return q.startswith('PORT:')
 def master(q):return '' if port(q) else cells[inst(q)]['master']
 def transparent(q):return master(q).startswith(('BUF','INV','HB'))
 def driver(q):return pins[q]['dir']==('INPUT' if port(q) else 'OUTPUT')
 def clock(q):return pins[q]['role']=='CLOCK' or (port(q) and q=='PORT:ck_core') or q.endswith('/CLK')
 sig={n:[q for q in v if pins[q]['role'] not in ('POWER','GROUND')] for n,v in nets.items()}
 ds={n:[q for q in v if driver(q)] for n,v in sig.items()};ls={n:[q for q in v if not driver(q) and not clock(q)] for n,v in sig.items()}
 outs=collections.defaultdict(list)
 for q in pins:
  if not port(q) and driver(q) and pins[q]['role'] not in ('POWER','GROUND'):outs[inst(q)].append(q)
 def endpoints(q):
  todo=list(ls.get(pins[q]['net'],[]));seen=set();ends=set()
  while todo:
   x=todo.pop()
   if x in seen:continue
   seen.add(x)
   if transparent(x):
    for o in outs[inst(x)]:todo.extend(ls.get(pins[o]['net'],[]))
   else:ends.add(x)
  return ends
 roots=[]
 for d in ds.values():
  for q in d:
   if clock(q) or transparent(q):continue
   role='input' if port(q) else 'ff' if master(q).startswith('DFF') else 'tie' if master(q).startswith('TIE') else 'macro' if master(q).startswith('ot_') else 'comb'
   e=endpoints(q);roots.append({'driver':q,'role':role,'loads':len(e),'endpoints':sorted(e),'reach_um':max([sum(abs(a-b) for a,b in zip(pins[q]['xy'],pins[x]['xy'])) for x in e] or [0])})
 copies={i:1 for i in cells};iterations=[]
 for k in range(100):
  nxt=dict(copies)
  for r in roots:
   if r['role'] in ('input','macro'):continue
   n=sum(1 if port(e) else copies[inst(e)] for e in r['endpoints']);i=inst(r['driver']);nxt[i]=max(nxt[i],math.ceil(n/32))
  iterations.append(sum(n-1 for n in nxt.values()))
  if nxt==copies:break
  copies=nxt
 else:raise RuntimeError('copy fixedpoint did not converge')
 extra=collections.Counter();area=collections.Counter();details=[]
 for i,n in copies.items():
  if n==1:continue
  m=cells[i]['master'];r='ff' if m.startswith('DFF') else 'tie' if m.startswith('TIE') else 'comb';b=cells[i]['bbox'];a=(b[2]-b[0])*(b[3]-b[1]);extra[r]+=n-1;area[r]+=(n-1)*a;details.append({'cell':i,'master':m,'copies':n,'extra_area_um2':(n-1)*a})
 uncovered=[]
 for r in roots:
  if r['role'] in ('input','macro'):
   n=sum(1 if port(e) else copies[inst(e)] for e in r['endpoints'])
   if n>32:uncovered.append({'driver':r['driver'],'role':r['role'],'weighted_loads':n})
 def boundary(q,reverse=False):
  todo=[q];seen=set();ff=set();nonff=[];logic=set()
  while todo:
   x=todo.pop()
   if x in seen:continue
   seen.add(x)
   if master(x).startswith('DFF'):ff.add(inst(x));continue
   if not port(x) and not transparent(x) and not master(x).startswith(('TIE','TAP')):logic.add(inst(x))
   if not port(x) and master(x).startswith('ot_'):nonff.append(x);continue
   if port(x) and x!=q:nonff.append(x);continue
   if reverse:
    ns=ds.get(pins[x]['net'],[]) if not driver(x) else ins[inst(x)]
   else:ns=ls.get(pins[x]['net'],[]) if driver(x) else outs[inst(x)]
   if not ns:nonff.append(x)
   todo.extend(ns)
  return {'ff':sorted(ff),'nonff':sorted(nonff),'logic_before_first_ff':sorted(logic)}
 # Precompute cell inputs to avoid quadratic boundary lookup.
 ins=collections.defaultdict(list)
 for q in pins:
  if not driver(q) and not port(q) and pins[q]['role'] not in ('POWER','GROUND'):ins[inst(q)].append(q)
 bounds={q:boundary(q,pins[q]['dir']=='OUTPUT') for q in pins if port(q) and pins[q]['role'] not in ('POWER','GROUND') and not clock(q)}
 for q,b in bounds.items():
  immediate=(ds if pins[q]['dir']=='OUTPUT' else ls).get(pins[q]['net'],[])
  b['immediate_nonregister_cells']=sorted(set(inst(x) for x in immediate if not port(x) and not master(x).startswith('DFF')))
 with gzip.open(p/(stage+'.boundary.json.gz'),'wt') as f:json.dump(bounds,f)

 summary={'source_graph_sha256':hashlib.sha256((p/(stage+'.tsv')).read_bytes()).hexdigest(),'cells':len(cells),'ff':sum(c['master'].startswith('DFF') for c in cells.values()),'die_um':die,'std_area_um2':sum((c['bbox'][2]-c['bbox'][0])*(c['bbox'][3]-c['bbox'][1]) for c in cells.values() if not c['master'].startswith('ot_')),'roots':len(roots),'max_by_role':{r:max(x['loads'] for x in roots if x['role']==r) for r in set(x['role'] for x in roots)},'over32_by_role':dict(collections.Counter(x['role'] for x in roots if x['loads']>32)),'over405':sum(x['reach_um']>405 for x in roots),'max_reach_um':max(x['reach_um'] for x in roots),'copy_model':{'status':'conditional primitive replication lower bound; equivalent D/reset/set copies and load partition not yet RTL/native proven','iterations_extra_cells':iterations,'extra_by_role':dict(extra),'extra_area_um2':dict(area),'uncovered_input_or_macro_roots':uncovered,'clock_loads_added':extra['ff'],'details':details},'macros':{i:c for i,c in cells.items() if c['master'].startswith('ot_')},'multiple_driver_signal_nets':[n for n,d in ds.items() if n and len(d)>1],'ports_with_combin_before_register':sum(bool(b['logic_before_first_ff']) for b in bounds.values()),'ports_with_unregistered_termination':sum(bool(b['nonff']) for b in bounds.values()),'port_count':len(bounds),'pg_unconnected_pins':[q for q,v in pins.items() if v['role'] in ('POWER','GROUND') and not v['net']]}
 (p/(stage+'.summary.json')).write_text(json.dumps(summary,indent=2)+'\n')
 with gzip.open(p/(stage+'.census.json.gz'),'wt') as f:json.dump(sorted(roots,key=lambda x:-x['loads']),f)
 with gzip.open(p/(stage+'.graph.tsv.gz'),'wb') as f:f.write((p/(stage+'.tsv')).read_bytes())
