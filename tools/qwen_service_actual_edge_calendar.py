#!/usr/bin/env python3
"""Actual fractional edge eligibility lower bounds, not an ideal controller clock."""
import json
from pathlib import Path
CORE=833333
CTL=1024000
# Balanced accumulator edge schedule: minimum n inter-pulse intervals.
def shortest_fs(n):
    return (n*CTL//CORE)*CORE

def model():
    checks={
      'tCCD_S':(1,1024000), 'tRCD':(19,19375000),'tRCDWR':(10,9375000),
      'tRP':(16,16250000),'tRAS':(28,28125000),'tRTP':(6,5625000),
      'tRRD_S':(3,2500000),'tRRD_L':(4,3125000),'tFAW':(15,15000000),
      'tRFC':(342,350000000),'tRFCpb':(196,200000000),'tRTW':(10,9948000),
      'tWTR_L_with_CWL_BL8':(14,(6250+1024+6250)*1000),
      'tWR_with_CWL_BL8':(28,(6250+1024+20625)*1000)}
    rows={}
    for k,(n,req) in checks.items():
      needed=n
      while shortest_fs(needed)<req:needed+=1
      rows[k]=dict(existing_counter_edges=n,min_actual_elapsed_fs=shortest_fs(n),required_fs=req,
        guaranteed_at_existing_count=shortest_fs(n)>=req,minimum_guaranteeing_edges=needed,
        additional_wait_edges=needed-n)
    return dict(core_fs=CORE,ctl_average_fs=CTL,eligibility=rows,
      scope='phase-universal edge lower bounds; actual command witness required, not a full DRAM proof',
      clock_gate_and_loaded_SSFF='unqualified',fix_selected=False,
      candidate_model='new minimum one additional-edge column eligibility guard/PC would add state and reduce service rate; not zero-cycle',
      worst_sustained_column_service='at most one column per two service edges if conservative guard selected; model actual token exposure before RTL')
if __name__=='__main__':
    print(json.dumps(model(),indent=2))
