"""Certify clone-vs-mapped capture convergence without initial-state equality.

Primitive transition functions must come from the separately couponed library.
This is not a theorem that synthesis preserved source RTL arithmetic.
"""
import argparse,hashlib,json
from pathlib import Path
from svc7_bound_graph import bound,emit

a=argparse.ArgumentParser(description=__doc__)
a.add_argument('mapped',type=Path);a.add_argument('native',type=Path)
a.add_argument('--top',required=True);a.add_argument('--name',required=True)
a.add_argument('--limit',type=int,default=24);a.add_argument('--out',type=Path,required=True)
x=a.parse_args();raw=x.mapped.read_bytes()
m,c,ins,outs,orig,n=bound(json.loads(raw),x.top,x.limit,['clk'],incremental=True)
text=emit(m,c,ins,outs,x.name)
assert text==x.native.read_text(),'native source not reproduced by exact primitive-family ledger'
drivers={b:k for k,v in c.items() for p,bs in v['connections'].items() if v['port_directions'][p]=='output' for b in bs}
clock=set(m['ports']['clk']['bits']);memo={};active=set()
def depth(k):
    if k in memo:return memo[k]
    assert k not in active,('feedback frontier',k)
    active.add(k);cell=c[k];ff=cell['type'].startswith('DFF')
    assert not cell['type'].startswith(('SDFF','LATCH','$')),cell['type']
    if ff:
        assert cell['type'] in ('DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R'),cell['type']
        assert ins[k]['CLK']==[(next(iter(clock)),0)],('noncanonical clock',k)
    deps=[depth(drivers[b]) for p,bs in ins[k].items() if p!='CLK' for b,inv in bs if b in drivers]
    v=max(deps+[0])+int(ff);active.remove(k);memo[k]=v;return v
for k in c:depth(k)
out={p:max([depth(drivers[b]) for b,inv in bs if b in drivers]+[0]) for p,bs in outs.items()}
r=dict(status='PASS_CLONE_VS_MAPPED_CAPTURE_DAG',mapped_sha256=hashlib.sha256(raw).hexdigest(),native_sha256=hashlib.sha256(text.encode()).hexdigest(),clones=n,cells=len(c),maximum_capture_depth=max(memo.values()),output_capture_depth=out,primitive_types=sorted({v['type'] for v in c.values()}),state_types=sorted({v['type'] for v in c.values() if v['type'].startswith('DFF')}),initial_state='Every original and copied FF initially arbitrary and independent; no equality assumed.',argument='Induct on acyclic primitive dependency graph. Primary inputs agree. Combinational functions agree once inputs agree. Each supported FF captures identical D/clock/reset function after its dependencies converge. Thus each family agrees by its capture depth and continues agreeing under arbitrary later input/reset changes.',scope='Clone versus mapped graph only. Requires exact pinned primitive truth coupons, startup/first-valid coverage before convergence, and source RTL versus mapped arithmetic correspondence separately. No layout or adoption claim.')
x.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
