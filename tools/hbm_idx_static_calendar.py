#!/usr/bin/env python3
"""Compile fixed INDEX microprogram, preserving implemented native latencies."""
import json,sys
from pathlib import Path
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
p=[];marks={}
def emit(index=0,weight=0,query=0,head=0,beat=0,op=0,ps=0,addr=0,flush=0,link=0,group=0):
 p.append(weight<<31|query<<30|head<<29|beat<<28|index<<20|op<<16|ps<<14|addr<<6|flush<<5|link<<4|group)
def wait(n):
 for _ in range(n):emit()
emit(weight=1,op=1);wait(16)
for q in range(128):emit(query=1,index=q)
wait(28)
for h in range(32):emit(head=1,index=h)
wait(100)
emit(op=3)
marks['first_key']=len(p)
for t in range(294):emit(beat=int(t<171),index=t if t<171 else 0,op=2 if t>=123 else 0,addr=t-123 if t>=123 else 0)
wait(2)
for b in range(31,-1,-1):emit(op=5,addr=b)
wait(1)
for ps in (1,2):
 emit(op=3,ps=ps)
 for a in range(171):emit(op=4,ps=ps,addr=a)
 wait(2)
 for b in range(63 if ps==2 else 31,-1,-1):emit(op=5,ps=ps,addr=b)
 wait(1)
for a in range(171):emit(op=6,ps=2,addr=a)
wait(3);emit(flush=1);wait(1)
marks['first_emit_instruction']=len(p)
for b in range(16):emit(link=1,group=b);wait(7)
wait(4)
assert len(p)<=2048
rows=[sum((p[i+j]if i+j<len(p)else 0)<<(32*j)for j in range(8))for i in range(0,len(p),8)]
(out/'calendar.hex').write_text(''.join(f'{r:064x}\n'for r in rows))
(out/'calendar_instructions.hex').write_text(''.join(f'{r:08x}\n'for r in p))
(out/'calendar.json').write_text(json.dumps(dict(length=len(p),rows=len(rows),marks=marks,scope='sourcecompiled schedule; nativeparent measured timeline/price OPEN'),indent=2)+'\n')
