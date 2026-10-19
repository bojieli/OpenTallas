import sys,re,json,collections,hashlib
from functools import lru_cache
src,out=sys.argv[1:]
cells={};pins=[];ports=[];dbu=1
for line in open(src):
 a=line.rstrip('\n').split('\t')
 if a[0]=='META': dbu=int(a[2])
 elif a[0]=='CELL':cells[a[1]]={'master':a[2],'macro':a[3]=='1','area':int(a[4])*int(a[5])/dbu**2}
 elif a[0]=='PIN':pins.append(a[1:])
 elif a[0]=='PORT':ports.append(a[1:])
def trans(c): return bool(re.match(r'^(BUF|INV)',cells[c]['master']))
def role(c):
 m=cells[c]['master']
 return 'macro' if cells[c]['macro'] else 'ff' if 'DFF' in m else 'tie' if m.startswith('TIE') else 'transparent' if trans(c) else 'comb'
def ck(pin,sig):return sig=='CLOCK' or bool(re.fullmatch(r'(?:CLK|CK|RCLK|WCLK|RD_CLK|WR_CLK)',pin,re.I))
loads=collections.defaultdict(list);drivers=collections.defaultdict(list);outputs=collections.defaultdict(list);unconnected=[];ambiguous=[];clockpins=[];pg=0
for c,p,d,s,n in pins:
 if s in ('POWER','GROUND'):pg+=1;continue
 if not n:unconnected.append((c,p,d,s));continue
 if ck(p,s):clockpins.append((c,p,n));continue
 if d=='OUTPUT':drivers[n].append((c,p));outputs[c].append(n)
 elif d=='INPUT':loads[n].append((c,p))
 else:ambiguous.append((c,p,d,s,n))
for p,d,s,n in ports:
 if s in ('POWER','GROUND'):continue
 if ck(p,s):clockpins.append(('PORT',p,n));continue
 if d=='INPUT': drivers[n].append(('PORT',p))
 elif d=='OUTPUT':loads[n].append(('PORT',p))
 else:ambiguous.append(('PORT',p,d,s,n))
visiting=set()
@lru_cache(None)
def ends(n):
 if n in visiting: raise RuntimeError('transparent cycle '+n)
 visiting.add(n);e=set()
 for c,p in loads.get(n,[]):
  if c!='PORT' and trans(c):
   if len(outputs[c])!=1: raise RuntimeError('bad transparent outputs '+c)
   e.update(ends(outputs[c][0]))
  else:e.add((c,p))
 visiting.remove(n);return frozenset(e)
rows=[]
for n,ds in drivers.items():
 for c,p in ds:
  r='input' if c=='PORT' else role(c)
  e=ends(n)
  rows.append(dict(net=n,driver=p if c=='PORT' else c,pin=p,master='PORT' if c=='PORT' else cells[c]['master'],role=r,reset_named=bool(re.search('rst|reset',n+' '+c,re.I)),count=len(e),endpoints=sorted(e)))
rows.sort(key=lambda r:(-r['count'],r['driver'],r['pin']))
roots=[r for r in rows if r['role']!='transparent'];bad=[r for r in roots if r['count']>32]
summary=dict(schema='native_odb_pin_transparent_census.v1',source_sha256=hashlib.sha256(open(src,'rb').read()).hexdigest(),cells=len(cells),cell_roles=dict(collections.Counter(role(c) for c in cells)),area_by_role={r:sum(x['area'] for c,x in cells.items() if role(c)==r) for r in set(role(c) for c in cells)},logical_signal_pins=len(pins)-pg,clock_pins=len(clockpins),clock_pin_by_master=dict(collections.Counter(cells[c]['master'] if c!='PORT' else 'PORT' for c,p,n in clockpins)),clock_net_loads=dict(collections.Counter(n for c,p,n in clockpins)),driver_roots=len(roots),max_by_role={r:max(x['count'] for x in roots if x['role']==r) for r in set(x['role'] for x in roots)},root_roles=dict(collections.Counter(r['role'] for r in roots)),over32_count=len(bad),over32_by_role=dict(collections.Counter(r['role'] for r in bad)),reset_named_over32=sum(r['reset_named'] for r in bad),unconnected_pins=unconnected,ambiguous_pins=ambiguous,multidriven=[dict(net=n,drivers=ds) for n,ds in drivers.items() if len(ds)>1],undriven_signal_nets=[dict(net=n,loads=l) for n,l in loads.items() if n not in drivers],over32=bad,top=roots[:40],macro_instances={c:x for c,x in cells.items() if x['macro']},ff_instances=[c for c in cells if role(c)=='ff'])
json.dump(summary,open(out,'w'),indent=1)
json.dump(roots,open(out+'.all_roots.json','w'),indent=1)
print(json.dumps({k:v for k,v in summary.items() if k not in ('over32','top','ff_instances','unconnected_pins','undriven_signal_nets','multidriven','macro_instances')},indent=2))
print('unconnected',len(unconnected),'undriven',len(summary['undriven_signal_nets']),'multidriver',len(summary['multidriven']))
for r in bad[:50]:print(r['role'],r['driver'],r['pin'],r['net'],r['count'])
