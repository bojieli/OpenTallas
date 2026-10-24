#!/usr/bin/env python3
"""HBM-P5-RTLA: offline lock-step of two tb_hgi_coll_tkm_static_pt event traces.
Every twin event (write v/addr/mask/data, done, fault change) must equal the pinned event exactly SHIFT edges later,
event for event, and the twin END cycles must be pinned + SHIFT.  Exit 0 = LOCKSTEP PASS, 1 = FAIL."""
import sys
def load(p):
    ev,end=[],None
    for ln in open(p):
        f=ln.split()
        if f[0]=='END':end=(int(f[1]),int(f[2]))
        else:ev.append((int(f[0]),tuple(f[1:])))
    return ev,end
pin,tw,shift=sys.argv[1],sys.argv[2],int(sys.argv[3])
(pe,pend),(te,tend)=load(pin),load(tw)
errs=[]
if pend is None or tend is None:errs.append('missing END')
elif tend!=(pend[0]+shift,pend[1]):errs.append(f'END pinned {pend} twin {tend} shift {shift}')
if len(pe)!=len(te):errs.append(f'event count pinned {len(pe)} twin {len(te)}')
for i,(a,b) in enumerate(zip(pe,te)):
    if b[0]!=a[0]+shift or b[1]!=a[1]:
        errs.append(f'event {i}: pinned t{a[0]} {a[1][:3]} twin t{b[0]} {b[1][:3]}')
        if len(errs)>8:break
writes=sum(1 for e in pe if e[1][0]=='1')
if errs:
    print('TKM_LOCKSTEP FAIL',len(errs),'first:',*errs[:6],sep='\n ');sys.exit(1)
print(f'TKM_LOCKSTEP PASS events={len(pe)} writes={writes} shift={shift} pinned_cycles={pend[0]} twin_cycles={tend[0]}')
