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
# Every native pin, constant owner and state role, without placement assumptions.
pins=[]; unconnected=[]
for i in insts.values():
 for t in i.getITerms():
  p=t.getMTerm(); n=t.getNet(); r=dict(instance=i.getName(),master=i.getMaster().getName(),pin=p.getName(),direction=str(t.getIoType()),signal=str(t.getSigType()),net=n.getName() if n else None)
  pins.append(r)
  if n is None and r['signal'] not in ('POWER','GROUND'): unconnected.append(r)
net_issues=[]
for n in b.getNets():
 ds=netdrivers[n.getName()]
 if len(ds)!=1 and loads[n.getName()]: net_issues.append(dict(net=n.getName(),drivers=ds,loads=loads[n.getName()]))
for r in records:
 if r['role']=='input':
  r['first_endpoints']=[dict(instance=i,pin=p,master=insts[i].getMaster().getName() if i!='PORT' else 'PORT') for i,p in r['endpoints']]
 elif r['role']=='ff':
  r['inputs']=[dict(pin=t.getMTerm().getName(),net=t.getNet().getName() if t.getNet() else None,owners=netdrivers[t.getNet().getName()] if t.getNet() else []) for t in insts[r['driver']].getITerms() if str(t.getIoType())=='INPUT']
# Terminal inversion parity is derived from every transparent native owner.
inv_members=collections.Counter(tuple(e) for r in records if r['role']=='transparent' and r['master'].startswith('INV') for e in r['endpoints'])
for r in functional:
 r['terminal_inversions']=[inv_members[tuple(e)]%2 for e in r['endpoints']]
result.update(pin_inventory=pins,unconnected_signal_pins=unconnected,net_driver_issues=net_issues,master_counts=dict(collections.Counter(i.getMaster().getName() for i in insts.values())),boundary_outputs=[dict(port=p.getName(),net=p.getNet().getName() if p.getNet() else None,sequential_ancestors=sorted(ancestry(p.getNet().getName(),set())) if p.getNet() else []) for p in b.getBTerms() if str(p.getIoType())=='OUTPUT'],scope='UNCHANGED HB1 UNPLACED native graph diagnostic; no physical qualification')
import gzip
with gzip.open(sys.argv[2], 'wt') as f: json.dump(result,f,separators=(',',':'))
summary={k:v for k,v in result.items() if k not in ('records','over32','pin_inventory','boundary_outputs')}
summary['over32_count']=len(result['over32']); summary['over32_by_role']=dict(collections.Counter(r['role'] for r in result['over32']))
json.dump(summary,open(sys.argv[3],'w'),indent=2)
print(json.dumps(summary))
