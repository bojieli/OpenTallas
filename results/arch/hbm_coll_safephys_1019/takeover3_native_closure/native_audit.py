import odb,sys,json,re,hashlib,collections,gzip
from functools import lru_cache
from pathlib import Path
src,out=map(Path,sys.argv[1:3]);db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def blocks(s,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',s):
  a=i=m.end();d=1
  while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip('" '),s[a:i-1]
roles={};lib_sources=[]
for lp in Path('/OpenROAD-flow-scripts/flow/platforms/asap7').rglob('*RVT_TT*.lib*'):
 text=gzip.open(lp,'rt').read() if lp.suffix=='.gz' else lp.read_text();lib_sources.append({'path':str(lp),'sha256':hashlib.sha256(lp.read_bytes()).hexdigest()})
 for mn,body in blocks(text,'cell'):
  pins={}
  for pn,pbody in blocks(body,'pin'):
   direction=re.search(r'\bdirection\s*:\s*(\w+)',pbody);function=re.search(r'\bfunction\s*:\s*"([^"]+)"',pbody);clock=re.search(r'\bclock\s*:\s*true',pbody)
   pins[pn]={'direction':direction[1] if direction else None,'function':function[1] if function else None,'clock':bool(clock)}
  inp=[k for k,v in pins.items() if v['direction']=='input'];outs=[(k,v) for k,v in pins.items() if v['direction']=='output'];fn=outs[0][1]['function'] if len(outs)==1 else None
  roles[mn]={'pins':pins,'unary':len(inp)==1 and len(outs)==1 and fn is not None and re.sub(r'[()\s]','',fn) in [inp[0],'!'+inp[0],inp[0]+"'"]}
actual={i.getMaster().getName() for i in b.getInsts()};unknown=sorted(actual-set(roles));macro_unknown=[n for n in unknown if next(i for i in b.getInsts() if i.getMaster().getName()==n).getMaster().isBlock()]
pgonly_unknown=[n for n in unknown if all(str(p.getSigType()) in ['POWER','GROUND'] for p in next(i for i in b.getInsts() if i.getMaster().getName()==n).getMaster().getMTerms())]
unknown_std=sorted(set(unknown)-set(macro_unknown)-set(pgonly_unknown))
if unknown_std:raise RuntimeError('native standard masters without pinned Liberty: '+str(unknown_std))
loads=collections.defaultdict(list);drivers=[];points={};rects={};trans={};pg=[];missing=[];clock=[];clock_seeds=set();dangling_transparent={}
def boxpoint(pin):
 if hasattr(pin,'getBBox'):
  z=pin.getBBox();return (z.xMin()/u,z.yMin()/u,z.xMax()/u,z.yMax()/u)
 return None
for i in b.getInsts():
 m=i.getMaster();mn=m.getName();transparent=roles.get(mn,{}).get('unary',False);outs=[];ins=[]
 for p in i.getITerms():
  mt=p.getMTerm();key=i.getName()+'/'+mt.getName();n=p.getNet();sid=n.getId() if n else None;st=str(mt.getSigType());io=str(mt.getIoType())
  rects[key]=boxpoint(p);points[key]=((rects[key][0]+rects[key][2])/2,(rects[key][1]+rects[key][3])/2) if rects[key] else None
  if st in ['POWER','GROUND']:
   pg.append((key,sid));continue
  if sid is None:missing.append(key);continue
  if io=='OUTPUT':drivers.append((key,sid,mn));outs.append(sid)
  elif io=='INPUT':
   loads[sid].append((key,st));ins.append(key)
   if st=='CLOCK' or roles.get(mn,{}).get('pins',{}).get(mt.getName(),{}).get('clock'):clock_seeds.add(sid);loads[sid][-1]=(key,'CLOCK')
  else:missing.append('UNKNOWN_DIRECTION:'+key+':'+io)
 if transparent:
  if len(outs)>1:raise RuntimeError('transparent outputs '+i.getName())
  if not outs:
   for key in ins:dangling_transparent[key]=next((p.getNet().getId() for p in i.getITerms() if i.getName()+'/'+p.getMTerm().getName()==key and p.getNet()),None)
   continue
  for key in ins:trans[key]=outs[0]
for p in b.getBTerms():
 if str(p.getSigType()) in ['POWER','GROUND']:continue
 n=p.getNet();key='PORT/'+p.getName();rects[key]=boxpoint(p);points[key]=((rects[key][0]+rects[key][2])/2,(rects[key][1]+rects[key][3])/2) if rects[key] else None
 if not n:missing.append(key);continue
 if str(p.getIoType())=='INPUT':drivers.append((key,n.getId(),'PORT'))
 elif str(p.getIoType())=='OUTPUT':loads[n.getId()].append((key,str(p.getSigType())))
net_drivers=collections.defaultdict(list)
for key,net,m in drivers:net_drivers[net].append(key)
trans_inputs={i.getName()+'/'+p.getMTerm().getName():p.getNet().getId() for i in b.getInsts() for p in i.getITerms() if p.getNet() and i.getName()+'/'+p.getMTerm().getName() in trans}
clock_links=collections.defaultdict(set)
for key,innet in trans_inputs.items():
 outnet=trans[key];clock_links[innet].add(outnet);clock_links[outnet].add(innet)
clock_nets=set(clock_seeds);todo=list(clock_seeds)
while todo:
 net=todo.pop()
 for other in clock_links[net]:
  if other not in clock_nets:clock_nets.add(other);todo.append(other)
open_clock_loads={key for key,net in dangling_transparent.items() if net in clock_nets}
@lru_cache(None)
def terminals(net):
 result=set()
 for key,st in loads[net]:
  if key in trans:result.update(terminals(trans[key]))
  else:result.add((key,'CLOCK' if key in open_clock_loads else st))
 return frozenset(result)
for net in list(clock_nets):
 for key,st in terminals(net):
  if key in dangling_transparent:open_clock_loads.add(key)
terminals.cache_clear()
rows=[];clockrows=[]
for key,net,m in drivers:
 ends=terminals(net);ck=[k for k,s in ends if s=='CLOCK'];data=[k for k,s in ends if s!='CLOCK'];d=points.get(key)
 distances=[(abs(d[0]-points[k][0])+abs(d[1]-points[k][1]),k) for k in data if d and points.get(k)]
 far=max(distances,default=(0,None));rb=rects.get(key);upper=max(((max(abs(rb[x]-rects[k][y])+abs(rb[a]-rects[k][z]) for x in [0,2] for y in [0,2] for a in [1,3] for z in [1,3]),k) for k in data if rb and rects.get(k)),default=(0,None));r={'driver':key,'master':m,'net':b.findNet(next(n.getName() for n in b.getNets() if n.getId()==net)).getName() if False else net,'terminals':len(data),'clock_terminals':len(ck),'max_L1_pin_centers_um':far[0],'worst_sink':far[1],'endpoints':data,'max_L1_pin_bbox_upper_um':upper[0],'worst_bbox_sink':upper[1]}
 rows.append(r)
 if ck:clockrows.append({'driver':key,'clock_terminals':len(ck),'data_terminals':len(data)})
summary={'schema':'opentallas.native_all_driver_endpoint_audit.v5','master_roles':{n:roles.get(n,{'role':'native_macro_MTerm_only'}) for n in sorted(actual)},'lib_sources':lib_sources,'unknown_std_masters':unknown_std,'odb_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'native_cells':len(b.getInsts()),'drivers':len(rows),'transparent_cells':sum(roles.get(i.getMaster().getName(),{}).get('unary',False) for i in b.getInsts()),'clock_role_authority':'Pinned Liberty clock:true and native MTerm CLOCK seeds traced bidirectionally through actual Liberty unary function connectivity; floating-output transparent loads on these proven trees counted as clock, never by instance name','open_clock_loads':sorted(open_clock_loads),'max_L1_pin_bbox_upper_um':max(r['max_L1_pin_bbox_upper_um'] for r in rows),'over32':[r for r in rows if r['terminals']>32],'reach_over405':[r for r in rows if r['max_L1_pin_bbox_upper_um']>405],'max_fanout':max(r['terminals'] for r in rows),'max_L1_pin_centers_um':max(r['max_L1_pin_centers_um'] for r in rows),'clock_rows':clockrows,'pg_iterms':len(pg),'pg_unbound':[k for k,n in pg if n is None],'missing_or_unknown':missing,'scope':'Actual native postCTS/global-route metadata + transformed pin bbox centers. PG conductor/via/short proof not performed. Full transformed native pin-bbox corner L1 upper bounds reported. Open clock loads retained in separate role.'}
out.mkdir(exist_ok=True);(out/'summary.json').write_text(json.dumps(summary,indent=2));(out/'rows.json').write_text(json.dumps(rows));print(json.dumps({k:v for k,v in summary.items() if k not in ['over32','reach_over405','clock_rows','pg_unbound','missing_or_unknown']}));print('OVER32',len(summary['over32']),'FAR405',len(summary['reach_over405']),'PG_UNBOUND',len(summary['pg_unbound']))
