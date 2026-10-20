import odb,sys,json,re,gzip,hashlib,collections
from pathlib import Path
from functools import lru_cache
src=Path(sys.argv[1]);out=Path(sys.argv[2]);db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def blocks(s,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',s):
  a=i=m.end();d=1
  while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip('" '),s[a:i-1]
roles={};libs=[]
for p in Path('/OpenROAD-flow-scripts/flow/platforms/asap7').rglob('*RVT_TT*.lib*'):
 text=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text();libs.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 for mn,body in blocks(text,'cell'):
  pins={}
  for pn,pb in blocks(body,'pin'):
   di=re.search(r'\bdirection\s*:\s*(\w+)',pb);fn=re.search(r'\bfunction\s*:\s*"([^"]+)"',pb)
   pins[pn]={'direction':di[1] if di else None,'function':fn[1] if fn else None,'clock':bool(re.search(r'\bclock\s*:\s*true',pb))}
  roles[mn]={'pins':pins,'seq':bool(re.search(r'\b(ff|latch)\s*\(',body))}
def point(p):
 z=p.getBBox();return [(z.xMin()+z.xMax())/2/u,(z.yMin()+z.yMax())/2/u]
nodes={};drivers=collections.defaultdict(list);targets=[];insts={};errors=[]
for i in b.getInsts():
 master=i.getMaster();mn=master.getName();macro=master.isBlock();role=roles.get(mn);seq=role and role['seq'];kind='macro' if macro else ('seq' if seq else 'comb');insts[i.getName()]={'master':mn,'kind':kind,'bbox':[v/u for v in [i.getBBox().xMin(),i.getBBox().yMin(),i.getBBox().xMax(),i.getBBox().yMax()]],'orient':str(i.getOrient())};ip={p.getMTerm().getName():p for p in i.getITerms() if str(p.getSigType()) not in ['POWER','GROUND']}
 if not macro and not role and ip:errors.append('unknown master '+mn);continue
 for pn,p in ip.items():
  if not p.getNet():continue
  di=str(p.getIoType());clock=str(p.getSigType())=='CLOCK' or (role or {}).get('pins',{}).get(pn,{}).get('clock');key=i.getName()+'/'+pn;nodes[key]={'inst':i.getName(),'pin':pn,'kind':kind,'point':point(p),'net':p.getNet().getId(),'direction':di,'clock':bool(clock)}
  if di=='OUTPUT':
   deps=[]
   if kind=='comb':
    fn=role['pins'].get(pn,{}).get('function')
    if fn is None:errors.append('missing combinational function '+key);continue
    deps=[q.getNet().getId() for qn,q in ip.items() if q.getNet() and str(q.getIoType())=='INPUT' and re.search(r'(?<![A-Za-z0-9_])'+re.escape(qn)+r'(?![A-Za-z0-9_])',fn)]
   drivers[p.getNet().getId()].append((key,deps))
  elif di=='INPUT' and kind in ['seq','macro'] and not clock:targets.append(key)
for p in b.getBTerms():
 if str(p.getSigType()) in ['POWER','GROUND'] or not p.getNet():continue
 key='PORT/'+p.getName();di=str(p.getIoType());nodes[key]={'inst':'PORT','pin':p.getName(),'kind':'port','point':point(p),'net':p.getNet().getId(),'direction':di,'clock':str(p.getSigType())=='CLOCK'}
 if di=='INPUT':drivers[p.getNet().getId()].append((key,[]))
 elif di=='OUTPUT':targets.append(key)
print('STAGE parsed',len(insts),len(nodes),'targets',len(targets),'roles',len(roles),flush=True)
active=set()
@lru_cache(None)
def roots(net):
 if net in active:raise RuntimeError('combinational cycle '+str(net))
 active.add(net);res=set()
 for key,deps in drivers[net]:
  if nodes[key]['kind']=='comb':
   for dep in deps:res.update(roots(dep))
  else:res.add(key)
 active.remove(net);return frozenset(res)
edges=[];mx=(0,None);counts=collections.Counter()
for dst in targets:
 for srcpin in roots(nodes[dst]['net']):
  if nodes[srcpin]['clock']:continue
  pair=[srcpin,dst];edges.append(pair);counts[nodes[srcpin]['kind']+'->'+nodes[dst]['kind']]+=1;a=nodes[srcpin]['point'];z=nodes[dst]['point'];dist=abs(a[0]-z[0])+abs(a[1]-z[1]);mx=max(mx,(dist,pair),key=lambda x:x[0])
print('STAGE edges',len(edges),flush=True)
used={p for e in edges for p in e};used_insts={nodes[p]['inst'] for p in used};result={'schema':'opentallas.qbank.actual_full_stage_graph.v1','source_odb':str(src),'odb_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'liberty':libs,'role_errors':sorted(set(errors)),'endpoint_nodes':{k:v for k,v in nodes.items() if k in used},'instances':{k:v for k,v in insts.items() if k in used_insts},'edges':edges,'edge_classes':dict(counts),'max_endpoint_L1_current_um':mx,'scope':'All actual combinational function dependencies collapsed from FF/macro/input to FF/macro/output. Clock pins excluded by native/Lib clock role; async data reset pins retained. Endpoint span is a necessary stage constraint, not detailed-route wirelength or timing.'}
with gzip.open(out,'wt') as f:json.dump(result,f)
print(json.dumps({'edges':len(edges),'nodes':len(used),'role_errors':len(result['role_errors']),'edge_classes':dict(counts),'max_endpoint_L1_current_um':mx}))
