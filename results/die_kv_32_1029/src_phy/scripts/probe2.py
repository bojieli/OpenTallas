import json,collections
C="/srv/opentallas-scratch2/claude/codex-kv-pg-0834/grid3_bbox"
pg=json.load(open(C+"/pg_rects.json"))
for n in ("VDD","VSS"):
  m8=[r for nn,ly,*r in pg if nn==n and ly=="M8"]
  ys=sorted(set(round(r[1],3) for r in m8));d=collections.Counter(round(b-a,3) for a,b in zip(ys,ys[1:]))
  L=collections.Counter(round(r[2]-r[0],0)//500*500 for r in m8)
  print(n,"M8 rows",len(ys),"dy",d.most_common(6),"len",sorted(L.items())[:12],"y0",ys[:4])
  m9=[r for nn,ly,*r in pg if nn==n and ly=="M9" and r[2]-r[0]>10]
  xs=sorted(set(round(r[0],3) for r in m9));print(n,"M9 cols",len(xs),collections.Counter(round(b-a,3) for a,b in zip(xs,xs[1:])).most_common(5))
