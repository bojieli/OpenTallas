#!/usr/bin/env python3
"""Enumerate actual hierarchical relay ports; no inferred geometry or phase claims."""
import argparse,gzip,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
mods=json.loads(a.netlist.read_text())['modules'];top='qfd_sp_vector_memory_par_partitioned';rows=[]
# A canonical net identity is either a top port bit or a hierarchy-local net bit.
# Port aliases are resolved recursively, preserving connections through wrappers.
tm=mods[top];labels={b:f'{top}.{n}[{i}]' for n,v in tm['ports'].items() for i,b in enumerate(v['bits'])}
def wire(b,mp,path):return mp.get(b,f'{path}::bit{b}') if isinstance(b,int) else f'constant:{b}'
def walk(name,mp,path):
 for n,c in mods[name].get('cells',{}).items():
  t=c['type'];cp=path+'.'+n;cc={k:[wire(b,mp,path) for b in v] for k,v in c['connections'].items()}
  if t=='qvm_data256_native':
   rows.append({'instance':cp,'master':t,'clock':cc['clk'],'d':cc['d'],'q':cc['q']})
  elif t in mods and not mods[t].get('attributes',{}).get('blackbox',0):
   cm={b:label for pn,pv in mods[t]['ports'].items() for b,label in zip(pv['bits'],cc.get(pn,[]))};walk(t,cm,cp)
walk(top,labels,top)
assert len(rows)==289,len(rows)
assert all(len(r['d'])==len(r['q'])==256 for r in rows)
assert len({r['clock'][0] for r in rows})==289
raw={'scope':'Actual elaborated logical relay port identities only; d/q are not assigned pins. No geometry, cuts, phase timing or physical qualification inferred. Parent write/control combinational paths still require graph expansion.','relay_tiles':len(rows),'rows':rows}
a.out.write_bytes(gzip.compress(json.dumps(raw,separators=(',',':')).encode(),mtime=0))
print(json.dumps({'relay_tiles':len(rows),'pins_per_relay':513,'data_input_bits':sum(len(r['d']) for r in rows),'data_output_bits':sum(len(r['q']) for r in rows),'distinct_clocks':289,'graph':str(a.out)}))
