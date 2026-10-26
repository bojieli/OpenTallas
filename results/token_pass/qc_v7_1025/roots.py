"""TOK-QK-QCV7 probe: CB16 cluster-root phase (cb16_dag.baseline, codex/qc-phase-2209@13f33606a) on a bound dir,
plus the root -> slice rs lane added stages (bind_sinks depth - asbuilt), per cluster."""
import sys,json,collections
sys.path.insert(0,sys.argv[4]); import cb16_dag as D
from pathlib import Path
b=Path(sys.argv[1]); inp,gid,r8,groups=D.load(b,Path(sys.argv[2])); old=D.baseline(inp)
sinks=json.loads((b/'bind_sinks.json').read_text())
asb={}
for g in groups['landing']:
    for m in g['members']:
        for a,c in m['sink_bits']:
            for bit in range(a,c+1): asb[g['sink'],m['sink_port'],bit]=m['asbuilt_stages']
rs=collections.defaultdict(set)
for k,v in sinks.items():
    if v[0]!='pin' or not v[1].startswith('c16_') or '.u_t_0_0.' not in v[1]: continue
    lp,bit=k.rsplit('[',1);leaf,p=lp.rsplit('.',1)
    if leaf.startswith('c16_'): continue
    a=asb.get((leaf,p,int(bit[:-1])));rs[v[1].split('.')[0]].add((leaf+'.'+p, v[2]-(a or 0), a is None))
out={}
for c in sorted({l.split('.')[0] for l in inp}):
    r=old(c+'.u_t_0_0','n_y'); out[c]=dict(root=r,rs=sorted(rs[c]))
json.dump(out,open(sys.argv[3],'w'),indent=1)
print('ROOTS',collections.Counter(v['root'] for v in out.values()))
print('RS',collections.Counter(tuple(x[1] for x in v['rs']) for v in out.values()))
