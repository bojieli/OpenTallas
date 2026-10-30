#!/usr/bin/env python3
"""DIE-KV-36 KV-022 iter2: rewrite OT_CLAND window rects for named groups in a kit landing_placement.tcl (fix-only).
usage: patch_win.py KIT name=x0,y0,x1,y1 [...]   -> prints old/new, fails if a name is missing."""
import re,sys,json
k=sys.argv[1]; p=k+"/landing_placement.tcl"; t=open(p).read(); log=[]
for a in sys.argv[2:]:
    n,r=a.split("="); new=" ".join("%.5f"%float(v) for v in r.split(","))
    pat=re.compile(r"(\{"+re.escape(n)+r" \{)([\d. ]+)(\})")
    m=pat.search(t); assert m, n
    log.append(dict(name=n,old=m.group(2),new=new)); t=pat.sub(lambda mm: mm.group(1)+new+mm.group(3),t,count=1)
open(p,"w").write(t); json.dump(log,open(k+"/patch_win_sd36.json","w"),indent=1); print(json.dumps(log))
