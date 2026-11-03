#!/usr/bin/env python3
"""TOK-QW-3: derive the nent1021 CTLM37 layout image from Codex's nent1013 gate image.
Later ranges [796,1012) move +8 (HEAD320->326 alignment, head_calendar_object later_range_relocation),
LOCAL37 1012 -> 1020. HEAD growth entries 796..803 are alignment padding (1<<116): this is a CTLM
range/user layout test image only, not an executable HEAD calendar."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'tools')
import residual2_calendar_candidate as R, programme_store as P
src=Path('g1');out=Path('g1021');(out/'rom').mkdir(parents=True,exist_ok=True)
words,dw=R.decode_image(src/'rom')
assert dw[0]&1023==1013 and dw[3]==(476<<16|320) and dw[4]==(796<<16|1)
M=(1<<128)-1
ent=lambda w,i:(w[i//4]>>(128*(i%4)))&M
E=[ent(words,i) for i in range(2048*4)]
local37=E[1012]; assert (local37&((1<<116)-1))==((14<<112)|(37<<4)|9)
N=E[:]
for i in range(796,1024):N[i]=0
for i in range(796,1012):N[i+8]=E[i]
for i in range(796,804):N[i]=1<<116
N[1020]=local37
for s in range(1,37):
    e=N[876+4*(s-1)];assert (e>>116)==8 and (e&((1<<116)-1))==((14<<112)|(s<<4)|9),s
W=[sum(N[4*a+k]<<(128*k) for k in range(4)) for a in range(2048)]
for lane in (0,1):
    (out/'rom'/f'calendar_m{lane}.viamap.hex').write_text(''.join(f'{w:0532x}\n' for w in P.physical_rows(W+[0]*2048,lane)[:256]))
nd=dw[:];nd[0]=(dw[0]&~1023)|1021;nd[3]=(476<<16)|326;nd[4]=(804<<16)|1
(out/'rom'/'dw.hex').write_text(''.join(f'{w:016x}\n' for w in nd))
w2,d2=R.decode_image(out/'rom');assert w2==W and d2==nd
print(json.dumps(dict(nent=1021,local37=1020,stage_local4_first=876,head=[476,326],opseg=804,dw=[f'{x:016x}' for x in nd])))
