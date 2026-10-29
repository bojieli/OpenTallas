#!/usr/bin/env python3
"""Read-only exact reach failure classification and existing TX-rung placement feasibility."""
import collections,inspect,json,sys,re
sys.path.insert(0,sys.argv[1]);import geom_rules as G
D=G.Design(sys.argv[2]);src=inspect.getsource(G.r2r_metrics)
src=src.replace('def r2r_metrics(D):','def collect(D):').replace('best, arg, n_gt = 0.0, None, 0','best, arg, n_gt = 0.0, None, 0\n    failures = []')
src=src.replace('if mx > R2R_MAX:\n            n_gt += 1','''if mx > R2R_MAX:
            n_gt += 1
            uu0=min(e[0] for e in lst);uu1=max(e[1] for e in lst);vv0=min(e[2] for e in lst);vv1=max(e[3] for e in lst)
            failures.append(dict(capture=D.cells[cap][6],source=D.cells[src][6],capture_xy=ctr(D.cells[cap]),source_xy=ctr(D.cells[src]),reach=mx,min_radius_fixed_sources=max((uu1-uu0)/2,(vv1-vv0)/2),launch_extents_uv=[uu0,uu1,vv0,vv1]))''')
src=src.replace('    name = lambda i:', '    D.reach_failures = failures\n    name = lambda i:')
ns=dict(G.__dict__);exec(src,ns);r=ns['collect'](D);f=D.reach_failures
banks=collections.defaultdict(list)
for x in f:
 n=x['capture'].replace('\\','');m=re.search(r'g_sl\[(\d+)\].*g_tx.g_r\[(\d+)\]',n);key=f'sl{m[1]}_r{m[2]}' if m else re.sub(r'\[\d+\]','[]',n)
 banks[key].append(x)
summary={k:dict(count=len(v),max_reach=max(x['reach'] for x in v),max_min_radius=max(x['min_radius_fixed_sources'] for x in v),first=v[0]) for k,v in banks.items()}
out=dict(metrics=r,failures=f,by_bank=summary,minimum_exceeds405=sum(x['min_radius_fixed_sources']>405 for x in f));open(sys.argv[3],'w').write(json.dumps(out,indent=1)+'\n')
print(json.dumps(dict(metrics=r,minimum_exceeds405=out['minimum_exceeds405'],by_bank={k:{a:b for a,b in v.items() if a!='first'} for k,v in summary.items()}),indent=1))
