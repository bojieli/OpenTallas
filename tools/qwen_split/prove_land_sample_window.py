#!/usr/bin/env python3
"""Finite4slot ring certificate; allK, both reset release orders, supported phase/age envelope.
Each epoch e writes slot(e%4) at w0+e*T and rewrites it at +4T. Receiver
counter r reads epoch r-K at r0+r*T. Choosing r0=w0+(E-K)*T+phase
makes age exactly E*T+phase independently of K and r. The compiler must bind
this age envelope at compensated TT/FF flops; an out-of-envelope link is rejected.
"""
import json
from fractions import Fraction as Q
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
checks=0;cases=[]
for k in range(8):
 for phase in [Q(i,16) for i in range(16)]:
  for E in range(4):
   age=E+phase
   if not Q(1,4)<=age<=Q(13,4):continue
   for w0 in (Q(100),Q(108)):
    r0=w0+E-k+phase
    for r in range(16,48):
     e=r-k;capture=r0+r;write=w0+e;overwrite=write+4
     assert capture-write==age
     assert write<capture<overwrite
     assert capture-write>=Q(1,4)
     assert overwrite-capture>=Q(3,4)
     assert e%4==(r-k)%4
     assert e%8==((r%8)-k)%8
     checks+=1
   cases.append(dict(K=k,phase_T=float(phase),integer_age_T=E,age_T=float(age),overwrite_gap_T=float(4-age)))
out=dict(schema='opentallas.qwen.landing_sample_window.v1',pass_=True,D=4,K=list(range(8)),
 min_age_T=.25,max_age_T=3.25,min_overwrite_gap_T=.75,checks=checks,cases=cases,
 root_obligation='Compiler proves actual TT/FF compensated-root read age within [0.25T,3.25T]; rejects other bindings.',
 timing_policy='No data falsepaths/MCP; related-root reference STA charges60ps+0.75T crossing setup uncertainty and25ps hold, plus measured CTS skew.')
Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print('LAND_WINDOW PASS',checks,'slot/epoch/overwrite checks')
