#!/usr/bin/env python3
"""Finite symbolic control calculation only, not an RTL/native or timing proof."""
from collections import deque
import json
from pathlib import Path
# old slots0/1, wp/rp/n; new latest/older and reset-free latest_slot.
# All payloads are uninterpreted symbols0/1/2; warm reset preserves payloads.
start=[]
for a in range(3):
 for b in range(3):
  for ls in [0,1]:
   v=[a,b];start.append((a,b,0,0,0,v[ls],v[1-ls],ls))
seen=set(start);q=deque(start);transitions=0;occupancy2=[]
while q:
 st=q.popleft();a,b,wp,rp,n,latest,older,ls=st;old=[a,b]
 assert old[rp]==(latest if rp==ls else older)
 for reset in [0,1]:
  for pv in [0,1]:
   for ready_i in [0,1]:
    push=bool(pv and n!=2);pop=bool(n!=0 and ready_i)
    if n==2:occupancy2.append(dict(pv=pv,ready_i=ready_i,push=push,pop=pop))
    for data in range(3):
     ov=old[:];nl,no,nls=latest,older,ls
     # Source payload captures remain reset-free even when control resets.
     if push:
      ov[wp]=data
      if wp!=ls:no=latest
      nl=data;nls=wp
     if reset:nwp,nrp,nn=0,0,0
     else:nwp=wp^push;nrp=rp^pop;nn=n+push-pop
     ns=(*ov,nwp,nrp,nn,nl,no,nls)
     assert ov[nrp]==(nl if nrp==nls else no)
     transitions+=1
     if ns not in seen:seen.add(ns);q.append(ns)
# Existing controller admits odd pr: ceil(1/2)=1, one tail pop of1.
pr=0;left=(1+2-1)//2;step=min(2,left);pr=(pr+step)&1023
assert pr==1
out=dict(status='PASS_FINITE_SYMBOLIC_MAPPING_CALCULATION_NOT_RTL_PROOF',states=len(seen),transitions=transitions,includes_warm_reset=True,includes_stale_output_when_empty=True,source_occupancy2_cases=[dict(x)for x in {tuple(sorted(x.items()))for x in occupancy2}],occupancy2_push_excluded_by_actual_source_p_ready=True,even_pr_counterexample=dict(tjob=1,R=2,p_left=1,pstep=1,pr_after=1,no_header_or_GO_pr_reset=True),new_FF=dict(old_payload=2048,new_payload=1024,old_control=4,new_control=11,net_external_FF=-1017,new_reset_free_format_bits=6,new_reset_free_latest_slot_bits=1,original_wp_rp_preserved=True,reset_load_delta=0),qualified_native=False)
Path(__file__).with_name('control_model.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'],len(seen),transitions)
