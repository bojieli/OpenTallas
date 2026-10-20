import odb, json, re, hashlib, sys, collections
from pathlib import Path
inp=Path(sys.argv[1]); out=Path(sys.argv[2]); db=odb.dbDatabase.create(); odb.read_db(db,str(inp)); block=db.getChip().getBlock(); units=block.getDbUnitsPerMicron()
netloads=collections.defaultdict(list); roots=[]; transparent={}; pgs=[]; masters=collections.Counter(); rolemasters=collections.defaultdict(set); openinv=set()
def xy(it):
 z=it.getAvgXY(); return [z[-2]/units,z[-1]/units] if z[0] else None
for inst in block.getInsts():
 master=inst.getMaster(); name=master.getName(); masters[name]+=1
 sig=[]
 if name.startswith(('INV','BUF','CKINVDC')) and all((it.getNet() is None or (len(it.getNet().getITerms())==1 and not it.getNet().getBTerms())) for it in inst.getITerms() if str(it.getMTerm().getIoType())=='OUTPUT'): openinv.add(inst.getName()); rolemasters['open_output_bufinv'].add(name)
 for it in inst.getITerms():
  mt=it.getMTerm(); net=it.getNet(); pn=mt.getName(); ident=inst.getName()+"/"+pn
  if str(mt.getSigType()) in ('POWER','GROUND'):
   if net is None:pgs.append(ident)
   continue
  if net is None: continue
  nk=net.getName(); direction=str(mt.getIoType()); sig.append((pn,nk,direction))
  isclock=(master.isBlock() or name.startswith(('DFF','SDFF'))) and pn in ('CLK','CK','clk','ck','CLKA','CLKB','clka','clkb','rclk','wclk')
  if direction=='INPUT': netloads[nk].append((ident,'clock' if isclock else 'data',xy(it)))
  elif direction=='OUTPUT': roots.append((ident,nk,name,xy(it)))
 if re.match(r'^(BUF|INV|CKINVDC)[xX]?',name) and len(sig)==2:
  ins=[n for p,n,d in sig if d=='INPUT']; outs=[n for p,n,d in sig if d=='OUTPUT']
  if len(ins)==len(outs)==1: transparent[inst.getName()]=(ins[0],outs[0]); rolemasters['transparent'].add(name)
for bt in block.getBTerms():
 if str(bt.getSigType()) in ('POWER','GROUND') or bt.getNet() is None:continue
 z=bt.getFirstPinLocation(); loc=[z[-2]/units,z[-1]/units] if z[0] else None
 if str(bt.getIoType())=='INPUT':roots.append(('TOP/'+bt.getName(),bt.getNet().getName(),'TOP_INPUT',loc))
 elif str(bt.getIoType())=='OUTPUT':netloads[bt.getNet().getName()].append(('TOP/'+bt.getName(),'data',loc))
cache={}
def ends(net,seen=frozenset()):
 if net in cache:return cache[net]
 if net in seen:raise RuntimeError('transparent loop '+net)
 terms=[]
 for ident,role,loc in netloads[net]:
  inst=ident.rsplit('/',1)[0]
  if inst in openinv:terms.append((ident,'open_output_bufinv',loc))
  elif inst in transparent:terms.extend(ends(transparent[inst][1],seen|{net}))
  else:terms.append((ident,'open_output_bufinv' if inst in openinv else role,loc))
 cache[net]=terms;return terms
rows=[]; clocks=[]
for driver,net,master,loc in roots:
 terminals=ends(net)
 row={'driver':driver,'net':net,'master':master,'terminal_pins':len(terminals),'clock_terminal_pins':sum(t[1]=='clock' for t in terminals)}
 if row['clock_terminal_pins']>0 and all(t[1] in ('clock','open_output_bufinv') for t in terminals):clocks.append(row);continue
 row['mixed_clock_data']=bool(row['clock_terminal_pins']); row['nonclock_terminal_examples']=[t[0] for t in terminals if t[1]=='data'][:8]
 if loc:row['max_pin_l1_um']=max((abs(loc[0]-t[2][0])+abs(loc[1]-t[2][1]) for t in terminals if t[2]),default=0)
 rows.append(row)
rows.sort(key=lambda r:-r['terminal_pins'])
res={'odb':str(inp),'odb_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'scope':'read-only actual ODB; all drivers; BUF/INV-transparent terminal pins; genuine all-clock terminal cones separate; no PG mutation','instances':sum(masters.values()),'masters':dict(masters),'open_output_bufinv_instances':sorted(openinv),'role_masters':{k:sorted(v) for k,v in rolemasters.items()},'unbound_pg_pin_count':len(pgs),'unbound_pg_examples':pgs[:20],'driver_count':len(rows),'max_nonclock_fanout':max((r['terminal_pins'] for r in rows),default=0),'over32':[r for r in rows if r['terminal_pins']>32],'mixed_clock_data':[r for r in rows if r['mixed_clock_data']],'top20':rows[:20],'clock_driver_count':len(clocks),'clock_max_terminal_pins':max((r['terminal_pins'] for r in clocks),default=0),'all_nonclock_drivers':rows,'clock_drivers':clocks,'max_pin_l1_um':max((r.get('max_pin_l1_um',0) for r in rows),default=0),'far405':[r for r in rows if r.get('max_pin_l1_um',0)>405]}
out.write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k not in ['masters','over32','top20','far405','mixed_clock_data','all_nonclock_drivers','clock_drivers']}))
