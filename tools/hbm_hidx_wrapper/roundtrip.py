import json,collections,hashlib
from pathlib import Path
original=json.loads(Path('out/netlist.json').read_text())['modules']['hidx_coupon1'];rt=json.loads(Path('out/roundtrip.json').read_text())['modules']['hidx_coupon1']
def normalized(m,roundtrip=False):
 cells={n:c for n,c in m['cells'].items() if c['type']!='$scopeinfo'}
 name_map={}
 for n in cells:
  # JSON internal $id becomes a public escaped Verilog identifier on parse.
  dest=n[1:] if roundtrip and n.startswith('\\$') and n[1:] in original['cells'] else n
  name_map[n]=dest
 assert len(set(name_map.values()))==len(name_map),'non-injective identifier escape map'
 if roundtrip:
  assert set(name_map.values())=={n for n,c in original['cells'].items() if c['type']!='$scopeinfo'},'unknown/lost native cells'
  Path('out/identifier_escape_map.json').write_text(json.dumps(name_map,indent=2)+'\n')
 nets=collections.defaultdict(list)
 for n,c in cells.items():
  for p,bs in c['connections'].items():
   for i,b in enumerate(bs):nets[b].append(('cell',name_map[n],c['type'],p,i,c['port_directions'][p]))
 for n,p in m['ports'].items():
  for i,b in enumerate(p['bits']):nets[b].append(('port',n,p['direction'],i))
 r=[]
 for b,ends in nets.items():
  if isinstance(b,str):ends.append(('constant',b))
  r.append(sorted(ends,key=str))
 return sorted(r,key=str)
a=normalized(original);b=normalized(rt,True)
if a!=b:
 aa={json.dumps(x) for x in a};bb={json.dumps(x) for x in b}
 Path('out/roundtrip_mismatch.json').write_text(json.dumps(dict(source_only=sorted(aa-bb)[:8],verilog_only=sorted(bb-aa)[:8],source_only_count=len(aa-bb),verilog_only_count=len(bb-aa)),indent=2)+'\n')
 raise AssertionError('JSON/Verilog endpoint-network mismatch')
sha=hashlib.sha256(json.dumps(a,separators=(',',':')).encode()).hexdigest()
Path('out/roundtrip_equivalence.json').write_text(json.dumps(dict(verdict='PASS',cell_pin_port_networks=len(a),canonical_and_all_added_native_pins=True,json_to_verilog_to_json_connectivity_sha256=sha,cell_netnames_may_differ=True,optimization=False),indent=2)+'\n')
