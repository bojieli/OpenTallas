from pathlib import Path
import re,sys
r=Path(__file__).resolve().parent
for dn in sys.argv[1:]:
 d=r/dn;s=(d/'pilot.def').read_text();cells=re.findall(r'^- (\S+) \S+ \+ FIXED \( (\d+) (\d+) \)',s,re.M)
 windows=[(int(x)-3000,int(y)-600,int(x)+4000,int(y)+900) for n,x,y in cells]
 def cut(b,w):
  x,y,X,Y=b;a,c,A,C=w
  if A<=x or a>=X or C<=y or c>=Y:return [b]
  a,c,A,C=max(a,x),max(c,y),min(A,X),min(C,Y)
  return [v for v in [(x,y,X,c),(x,C,X,Y),(x,c,a,C),(A,c,X,C)] if v[2]>v[0] and v[3]>v[1]]
 m=re.search(r'(?ms)^BLOCKAGES \d+ ;(.*?)^END BLOCKAGES',s);out=[]
 for ln in m[1].splitlines():
  q=re.fullmatch(r'- LAYER (M\d+) RECT \( (\d+) (\d+) \) \( (\d+) (\d+) \) ;',ln)
  if not q:continue
  l=q[1];bs=[tuple(map(int,q.groups()[1:]))]
  if l in ('M2','M3','M4','M5','M6','M7'):
   for w in windows:bs=[v for b in bs for v in cut(b,w)]
  out.extend(f'- LAYER {l} RECT ( {x} {y} ) ( {X} {Y} ) ;' for x,y,X,Y in bs)
 b=f'BLOCKAGES {len(out)} ;\n'+'\n'.join(out)+'\nEND BLOCKAGES'
 s=s[:m.start()]+b+s[m.end():];(d/'pilot.def').write_text(s)
 for f in ('feed_route.tcl','feed_sta.tcl'):(d/f).write_bytes((r/f).read_bytes())
 (d/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
O=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name codex-hbm-$(basename "$O") --memory=8g --memory-swap=8g --cpus=8 -v "$O:/o" openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /o/feed_route.tcl > /o/route.log 2>&1; for c in TT FF; do CORNER=$c openroad -no_init -threads 2 -exit /o/feed_sta.tcl > /o/sta_$c.log 2>&1; done'
''')
