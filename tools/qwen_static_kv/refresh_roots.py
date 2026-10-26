"""Normative RR REFpb reservation roots; no trace discovery or ready inputs.

A physical profile MUST bind the reset epoch/strap due phase and PHY/bridge
budgets before integration. This module derives only HBM controller roots.
"""
PERIOD=118;CYCLE=32*PERIOD;LEAD=28+16+4;RFC=196;IO_GUARD=8
# 8 PRE parity slots, 8 ACTs spaced by max(row parity,tRRDS,tRRDL), old RAS/RP,
# RCD and eight explicit pin/row stages. Each periodic REF costs pre/post8,
# its command slot and one forced PRE parity slot (19 edges).
BASE=28+16+8*2+8*4+19+8
WARM=BASE
while True:
 _next=BASE+19*((WARM+PERIOD-1)//PERIOD+1)
 if _next==WARM:break
 WARM=_next
assert WARM==176

def first_quiet(earliest,span,due_phase,bank_first):
    """Independently enumerate forbidden actual-bank intervals, not the RTL modulo formula."""
    candidate=earliest
    for _ in range(100):
        lo=candidate-WARM;hi=candidate+span+IO_GUARD
        conflicts=[]
        for bank in range(bank_first,bank_first+8):
            for cycle in range(lo//CYCLE-2,hi//CYCLE+2):
                due=due_phase+bank*PERIOD+cycle*CYCLE
                if lo<due+RFC and hi>due-LEAD:conflicts.append(due+RFC+WARM)
        if not conflicts:return candidate
        candidate=max(candidate+1,max(conflicts))
    raise ValueError('cannot find a deterministic quiet window')

def roots(now_phase,due_phase,k_sectors,v_sectors,v_not_before):
    if not (0<=now_phase<CYCLE and 0<=due_phase<CYCLE and 0<=v_not_before<=16000):raise ValueError('missing/invalid reset or readiness profile')
    nk,nv=len(k_sectors),len(v_sectors)
    if nk>256 or nv>256:raise ValueError('actual shape exceeds hardware')
    # Bank-group spacing is inferred from independent actual sector sequence.
    kd=[];last={};edge=0
    for sec in k_sectors:
        bg=sec&3;edge=max(edge,last.get(bg,-3)+3);kd.append(edge);last[bg]=edge;edge+=1
    vd=[i+(i//8)*5 for i in range(nv)]
    ks=kd[-1]+1 if kd else 0;vs=vd[-1]+1 if vd else 0
    kr=first_quiet(now_phase+WARM+2,ks,due_phase,0)
    vr=first_quiet(max(kr+ks+WARM+2,now_phase+v_not_before+WARM+2),vs,due_phase,16)
    return dict(kdesc=kr-now_phase-WARM,kgo=kr-now_phase-16,krd=kr-now_phase,
                vdesc=vr-now_phase-WARM,vgo=vr-now_phase-16,vrd=vr-now_phase,
                k_slots=[kr-now_phase+i for i in kd],v_slots=[vr-now_phase+i for i in vd],
                warmup_hbm=WARM,cycle_hbm=CYCLE,full_native_qualified=False)
