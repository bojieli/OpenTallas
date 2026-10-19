import json,hashlib,copy
from pathlib import Path
src=Path('canonical/netlist.json');j=json.loads(src.read_text());m=j['modules']['hidx_coupon1'];old=copy.deepcopy(m['cells'])
def sha(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
nextbit=1+max(b for n in m['netnames'].values() for b in n['bits'] if isinstance(b,int))
def bit():
 global nextbit
 r=nextbit;nextbit+=1;return r
clk=m['ports']['clk']['bits'][0]
def add(n,t,con):m['cells'][n]=dict(hide_name=0,type=t,parameters={},attributes={'keep':'00000000000000000000000000000001'},port_directions={p:('output' if p in ('Y','QN') else 'input') for p in con},connections={p:[b] for p,b in con.items()})
for port in ['compacted','pair_select','quad_select']:
 for i,b in enumerate(list(m['ports'][port]['bits'])):
  q=b
  if port=='compacted':
   d=bit();q=bit();add(f'wrapper_s1_inv_{i}','INVx1_ASAP7_75t_R',{'A':b,'Y':d});add(f'wrapper_s1_ff_{i}','DFFHQNx1_ASAP7_75t_R',{'D':d,'CLK':clk,'QN':q})
  out=bit();add(f'wrapper_output_{port}_{i}','BUFx8_ASAP7_75t_R',{'A':q,'Y':out});m['ports'][port]['bits'][i]=out
 # Yosys requires the exact output netname to carry its actual port bits.
 # Preserve original alias metadata under an explicit internal name instead.
 m['netnames']['canonical_output_'+port]=copy.deepcopy(m['netnames'][port])
 m['netnames'][port]['bits']=list(m['ports'][port]['bits'])
 m['netnames']['wrapper_abi_'+port]=dict(hide_name=0,bits=m['ports'][port]['bits'],attributes={})
assert all(m['cells'][n]==c for n,c in old.items())
Path('out/netlist.json').write_text(json.dumps(j)+'\n')
Path('out/identity.json').write_text(json.dumps(dict(canonical_json_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),canonical_cells_sha256=sha(old),retained_cells_sha256=sha({n:m['cells'][n] for n in old}),retained_records=len(old),retained_native_cells=sum(c['type']!='$scopeinfo' for c in old.values()),new_cells=len(m['cells'])-len(old),cell_connections_identical=True,arithmetic_resynthesis=False),indent=2)+'\n')
