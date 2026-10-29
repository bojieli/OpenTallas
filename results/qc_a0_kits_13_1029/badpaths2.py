import sys,inspect,json,collections
sys.path.insert(0,sys.argv[3]);import geom_rules as g
D=g.Design(sys.argv[1])
s=inspect.getsource(g.r2r_metrics).replace('def r2r_metrics(D):','def bad_paths(D):')
s=s.replace('        if mx > R2R_MAX:\n            n_gt += 1','        if mx > R2R_MAX:\n            n_gt += 1\n            sx,sy=ctr(D.cells[src]); BAD.append((round(mx,1),D.cells[src][6],round(sx,1),round(sy,1),D.cells[cap][6],round(x,1),round(y,1)))')
s=s.replace('    return dict(r2r_max=','    return BAD\n    return dict(r2r_max=')
g.BAD=[]
exec(s,g.__dict__);b=sorted(g.bad_paths(D),reverse=True)
json.dump(b,open(sys.argv[2],'w'),indent=0)
print('BAD',len(b))
import re
fam=collections.Counter()
for r in b:
    k=re.sub(r'\\\[\d+\\\]|\[\d+\]|\d+','#',r[1])[:50]+' -> '+re.sub(r'\\\[\d+\\\]|\[\d+\]|\d+','#',r[4])[:60]
    fam[k]+=1
for k,v in fam.most_common(15): print(v,k)
for r in b[:12]: print(r)
