from pathlib import Path
import sys,inspect,collections,json,re
O=Path('/srv/opentallas-scratch2/claude/codex-s81phys-2250/geom_xrt1')
sys.path.insert(0,str(O/'tools'));import geom_rules as G
s=inspect.getsource(G.r2r_metrics)
s=s.replace('best, arg, n_gt = 0.0, None, 0','rows=[]\n    best, arg, n_gt = 0.0, None, 0')
s=s.replace('n_gt += 1','n_gt += 1\n            rows.append((round(mx,2),src,cap))')
s=s[:s.index('    name = lambda')]+'    return rows\n'
ns=dict(vars(G));exec(s,ns)
D=G.Design(O/'geom.tsv');rows=ns['r2r_metrics'](D)
name=lambda c:D.cells[c][6].replace('\\','')
family=lambda n:re.sub(r'\[\d+\]','[*]',n.split('$_')[0])
groups=collections.Counter();out=[]
for d,a,b in sorted(rows,reverse=True):
 l,c=name(a),name(b);groups[family(l)+' -> '+family(c)]+=1
 out.append(dict(distance_um=d,launch=l,capture=c,launch_xy=G.ctr(D.cells[a]),capture_xy=G.ctr(D.cells[b])))
j=dict(count=len(rows),max_um=max(r[0] for r in rows),families=groups.most_common(),rows=out)
(O/'failure_families.json').write_text(json.dumps(j,indent=1)+'\n')
print(json.dumps({k:v for k,v in j.items() if k!='rows'},indent=1))
