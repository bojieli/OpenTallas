import collections, functools, hashlib, json, sys
import odb
db=odb.dbDatabase.create(); odb.read_db(db,sys.argv[1]); b=db.getChip().getBlock()
loads=collections.defaultdict(list); drivers=[]; insts={i.getName():i for i in b.getInsts()}
for i in b.getInsts():
 for p in i.getITerms():
  n=p.getNet()
  if n is None: continue
  r=(i.getName(),p.getMTerm().getName())
  if str(p.getIoType())=='OUTPUT': drivers.append((n.getName(),r,i.getMaster().getName()))
  elif str(p.getSigType()) not in ('POWER','GROUND'): loads[n.getName()].append(r)
for p in b.getBTerms():
 n=p.getNet()
 if n is None: continue
 if str(p.getIoType())=='INPUT': drivers.append((n.getName(),('PORT',p.getName()),'PORT'))
 elif str(p.getIoType())=='OUTPUT': loads[n.getName()].append(('PORT',p.getName()))
def trans(m): return m.startswith(('BUF','INV','HB'))
@functools.lru_cache(None)
def endpoints(net):
 out=set()
 for i,p in loads[net]:
  if i=='PORT': out.add((i,p)); continue
  inst=insts[i]; m=inst.getMaster().getName()
  if trans(m):
   op=[t.getNet().getName() for t in inst.getITerms() if str(t.getIoType())=='OUTPUT' and t.getNet()]
   assert len(op)<=1,(i,op)
   if op: out.update(endpoints(op[0]))
   else: out.add((i,p))
  elif p not in ('CLK','CK'): out.add((i,p))
 return frozenset(out)
records=[]
for net,(i,p),m in drivers:
 role='clock' if i=='PORT' and p=='clk' else 'input' if i=='PORT' else 'ff' if m.startswith('DFF') else 'tie' if m.startswith('TIE') else 'transparent' if trans(m) else 'comb'
 es=sorted(endpoints(net))
 records.append(dict(net=net,driver=i,pin=p,master=m,role=role,count=len(es),endpoints=es))
records.sort(key=lambda r:(-r['count'],r['driver']))
functional=[r for r in records if r['role'] not in ('transparent','clock')]
dbu=b.getDbUnitsPerMicron()
area_by_master={i.getMaster().getName():i.getMaster().getWidth()*i.getMaster().getHeight()/dbu**2 for i in insts.values()}
netdrivers=collections.defaultdict(list)
for net,(i,p),m in drivers: netdrivers[net].append((i,p,m))
def ancestry(net,seen):
 if net in seen: return set()
 seen.add(net); answer=set()
 for i,p,m in netdrivers[net]:
  if i=='PORT' or m.startswith('DFF'): answer.add(i); continue
  for t in insts[i].getITerms():
   if str(t.getIoType())=='INPUT' and str(t.getSigType()) not in ('POWER','GROUND') and t.getNet():
    answer.update(ancestry(t.getNet().getName(),seen))
 return answer
for r in functional:
 if r['count']>32 and r['role']=='comb': r['sequential_ancestors']=sorted(ancestry(r['net'],set()))
result=dict(area_by_master=area_by_master, schema='opentallas.xr6.uncapped_native_logical_pins.v1',odb=sys.argv[1],odb_sha256=hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),cells=len(insts),ff=sum(i.getMaster().getName().startswith('DFF') for i in insts.values()),drivers=len(records),max_by_role={k:max(r['count'] for r in records if r['role']==k) for k in sorted({r['role'] for r in records})},over32=[r for r in functional if r['count']>32],records=records)
json.dump(result,open(sys.argv[2],'w'),indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('records','over32')}))
print('OVER32',len(result['over32']))
for r in result['over32'][:30]: print(r['role'],r['driver'],r['pin'],r['count'])
