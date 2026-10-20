"""Feed-forward capture certificate, independent of register initialization.
This certifies clone-vs-mapped convergence, not RTL arithmetic equivalence.
"""
import hashlib,json,sys
from pathlib import Path
from svc7_bound_graph import bound,emit
raw=Path(sys.argv[1]).read_bytes();d=json.loads(raw)
m,c,ins,outs,origins,n=bound(d,'fan32_graph_input',24,['clk'])
text=emit(m,c,ins,outs,'ot_hdc_fp32_add_lat7_fan32_native')
assert text==Path(sys.argv[2]).read_text(),'native source does not reproduce'
drivers={b:name for name,x in c.items() for port,bits in x['connections'].items() if x['port_directions'][port]=='output' for b in bits}
clock=set(m['ports']['clk']['bits']); depths={};active=set()
def depth(name):
 if name in depths:return depths[name]
 assert name not in active,('CYCLE',name)
 active.add(name);x=c[name]
 assert x['type'].startswith(('DFFHQN','DFFASRHQN')) or not x['type'].startswith(('DFF','SDFF','LATCH')),x['type']
 deps=[drivers[b] for port,edges in ins[name].items() for b,iv in edges if b in drivers and b not in clock and port not in ('CLK','CK')]
 value=max([depth(dep) for dep in deps]+[0])+int(x['type'].startswith('DFF'))
 active.remove(name);depths[name]=value;return value
for name in c:depth(name)
outdepth={p:max([depth(drivers[b]) for b,iv in edges if b in drivers]+[0]) for p,edges in outs.items()}
assert outdepth=={'y':7,'err':7,'valid_out':7},outdepth
assert max(depths.values())==7
report=dict(status='PASS_CLONE_VS_MAPPED_FEEDFORWARD_CONVERGENCE',source_sha256=hashlib.sha256(raw).hexdigest(),native_sha256=hashlib.sha256(text.encode()).hexdigest(),clones=n,cells=len(c),max_capture_depth=7,output_capture_depth=outdepth,register_types=sorted({x['type'] for x in c.values() if x['type'].startswith('DFF')}),invariant='Reproduced native primitive inputs/outputs match original family functions, including reset and clock. Acyclic capture DAG converges in <=7 captures from arbitrary independent FF initialization.',scope='Clone versus mapped graph only. Reset/first-valid and RTL arithmetic correspondence remain separate obligations.')
print(json.dumps(report,indent=2))
