#!/usr/bin/env python3
"""Inventory every clock/reset terminal omitted by the inner data/control graph."""
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--graph',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();j=json.loads(a.graph.read_text());t=next(v for v in j['modules'].values()if v.get('attributes',{}).get('top')in[1,'1','00000000000000000000000000000001']);boundary={bit:(n,i)for n,v in t['ports'].items()for i,bit in enumerate(v['bits'])};rows=[]
for n,c in t['cells'].items():
 for port,bits in c['connections'].items():
  if port not in ['ck','clk','arst_n','rst']:continue
  for i,bit in enumerate(bits):
   assert c['port_directions'][port]=='input';assert bit in boundary,(n,port,bit)
   role='clock'if port in ['ck','clk']else'active_low_async_reset'
   rows.append({'instance':n,'master':c['type'],'declared_port':port,'bit':i,'direction':'input','role':role,'top_boundary_port':boundary[bit][0],'top_boundary_index':boundary[bit][1]})
assert len(rows)==76 and sum(r['role']=='clock'for r in rows)==38
report={'status':'EXPLICIT_INNER_CLOCK_RESET_TRANSPORT_INVENTORY_OPEN','graph_sha256':hashlib.sha256(a.graph.read_bytes()).hexdigest(),'data_control_census_scope':'10396 inner interchild joins only;8796 timed plus1600 actual mapped constants. Not fullparent allnets.','omitted_terminal_bits':76,'clock_terminal_bits':38,'reset_terminal_bits':38,'omitted_interchild_driven_joins':0,'rows':rows,'source_semantics':['All38 inner clocks are distinct direct ck[0..37] boundary bits; fullparent maps copy c to ck[1+38*c+:38].','Inner rst is active-low despite name: shcol/shctl always blocks use negedge rst; arithmetic uses same direct rst as arst_n. No internal leaf reset relay output is omitted.','Fullparent rst[0] directly feeds all152 physical child reset terminals; top ck0 reset_sync generates rn for top endpoint and relay/capture helpers. Those fullparent transport paths are outside this inner graph.','Root217 receipt records fullparent root roles0..216; physical clock tree, reset recovery/removal, asynchronous release synchronization, reset distribution skew, PG and all insertion/native checks remain OPEN.','No clock/reset path is assigned zero delay or counted in timed data/control joins.']}
a.out.write_text(json.dumps(report,indent=1)+'\n');print({k:report[k]for k in ['omitted_terminal_bits','clock_terminal_bits','reset_terminal_bits','omitted_interchild_driven_joins']})
