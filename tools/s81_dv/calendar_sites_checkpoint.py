#!/usr/bin/env python3
"""Report physical hops in an immutable placement checkpoint, without repair."""
import collections,json,pickle,sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path[:0]=[str(root/'input/src/tools/s81_dv'),str(root/'input/src/tools')]
import dv_rvcase
with open(root/sys.argv[2]/'before_repair.pickle','rb') as f:args,kw=pickle.load(f)
st,parent,kids,terms,placed,loc,placer,reach,boxes=args
hop=lambda a,b:sum(abs(x-y) for x,y in zip(a,b))
rows=[dict(kind='station',source=v,capture=u,hop=hop(placed[v],placed[u])) for v in st for u in kids[v]]
rows += [dict(kind='load',source=v,capture=t,hop=hop(placed[v],t)) for v in st for t in terms[v]]
over=sorted((r for r in rows if r['hop']>reach),key=lambda r:-r['hop'])
print(json.dumps(dict(stages=len(st),hops=len(rows),over=len(over),by_kind=dict(collections.Counter(r['kind'] for r in over)),worst=over[:30]),indent=1))
