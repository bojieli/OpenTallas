"""Independent generic source all-pin census of specialized actual-native source."""
import json,re,collections,hashlib
from pathlib import Path
p=Path('generic/source.json');d=json.load(open(p));top=d['modules']['qfd_tile_nk_regroot5_reset_native'];cells=top['cells'];loads=collections.defaultdict(set);drivers=[];outnet={}
for n,c in cells.items():
 for port,bits in c['connections'].items():
  direction=c['port_directions'][port]
  for j,bit in enumerate(bits):
   pin=n+'/'+port+('['+str(j)+']' if len(bits)>1 else '')
   if direction=='input':loads[bit].add(pin)
   elif direction=='output':drivers.append((pin,c['type'],bit,n));outnet[n]=bit
for n,c in top['ports'].items():
 for j,bit in enumerate(c['bits']):
  pin='PORT/'+n+('['+str(j)+']' if len(c['bits'])>1 else '')
  if c['direction']=='output':loads[bit].add(pin)
  else:drivers.append((pin,'INPUT_PORT',bit,None))
def terminals(bit,seen=None):
 seen=set() if seen is None else set(seen)
 if bit in seen:return set()
 seen.add(bit);found=set()
 for pin in loads[bit]:
  if pin.startswith('PORT/'):found.add(pin);continue
  n=pin.rsplit('/',1)[0];c=cells[n]
  if re.match(r'^(BUF|INV|HB).*ASAP7',c['type']):found.update(terminals(outnet[n],seen))
  else:found.add(pin)
 return found
rows=[]
for pin,master,bit,inst in drivers:
 ep=sorted(terminals(bit));clock=pin.startswith('PORT/ck')
 rows.append(dict(driver=pin,master=master,clock=clock,sequential=bool(re.search('DFF|LATCH|DHL',master)),transparent_loads=len(ep),endpoints=ep))
rows.sort(key=lambda x:(-x['transparent_loads'],x['driver']));bad=[r for r in rows if not r['clock'] and r['transparent_loads']>32];ff=[r for r in bad if r['sequential']]
assert len(cells)==38609,len(cells);assert sum('DFF' in c['type'] for c in cells.values())==15651
assert len(ff)==7,len(ff);assert max(r['transparent_loads'] for r in ff)==415
actual=json.load(open('native/census.json'));expected={r['driver']:(r['master'],r['transparent_loads']) for r in actual['violations']}
# Yosys unescapes '[' identifiers while OpenDB preserves escaped syntax.
def norm(s):return s.replace('\\','')
assert {norm(r['driver']):(r['master'],r['transparent_loads']) for r in ff}=={norm(k):v for k,v in expected.items()}
native_bad={norm(r['driver']):(r['master'],r['transparent_loads']) for r in actual['all_drivers'] if not r['clock'] and r['transparent_loads']>32}
assert {norm(r['driver']):(r['master'],r['transparent_loads']) for r in bad}==native_bad
report=dict(schema='opentallas.a0.generic_source_census.v1',source_sha256=hashlib.sha256(open('native/candidate.v','rb').read()).hexdigest(),cells=len(cells),native_ff=15651,nonclock_over32=len(bad),register_over32=len(ff),maximum_register_loads=max(r['transparent_loads'] for r in ff),violations=bad,all_drivers=rows,native_bad_registers_exactly_match=True,native_all_bad_drivers_exactly_match=True)
json.dump(report,open('generic/census.json','w'),indent=2)
print('A0_GENERIC_SOURCE_CENSUS_PASS',len(cells),'cells',len(ff),'broadFF',len(bad),'broadnonclock')
