import json,collections
from pathlib import Path
m=json.load(open('out/census/proxy.json'))['modules']['qfd_link_adp512_proxy_candidate']; roots=m['ports']['ck']['bits'];count=collections.Counter();other=collections.Counter();macros=collections.Counter()
for cell in m['cells'].values():
 t=cell['type']
 if 'DFF' in t:
  conn=cell['connections'];clock=conn.get('C',conn.get('CLK',[]));n=len(conn.get('Q',[]))
  for c in clock:count[roots.index(c) if c in roots else str(c)]+=n
  other[t]+=n
 elif 'sram' in t.lower():macros[t]+=1
out={'schema':'ot.qwen.proxy.census.v1','stage':'yosys generic bit synthesis noabc, real SRAM blackboxes','top':'qfd_link_adp512_proxy_candidate','params':{'ENABLE_PROXY':1,'MUT':0},'clock_root_sinks':dict(sorted(count.items(),key=lambda x:str(x[0]))),'aggregate_sequential_bits':sum(count.values()),'max_root_sinks':max(count.values()),'sequential_cell_types':dict(other),'macros':dict(macros),'cell_count':len(m['cells']),'not_qualification':'No placed pins/reach/corner timing, PG phase, clock insertion or power qualification.'}
Path('out/census/count.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
