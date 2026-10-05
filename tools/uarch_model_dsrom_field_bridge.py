#!/usr/bin/env python3
"""Additive DS field bridge resource/latency terms; original unified model pinned.
No RTL, compiler, launch or numerical payload. Unknown service costs stay unknown.
"""
import ast
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def unified_ff_um2():
    tree=ast.parse((ROOT/'tools/uarch_model.py').read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DFF_UM2' for t in node.targets):
            return Fraction(str(ast.literal_eval(node.value)))
    raise ValueError('missing unified FF unit')

def fault_coverage(np,roots):
    leaves=2*np
    if np<=0 or roots<=0 or np&(np-1) or roots&(roots-1) or roots>np:raise ValueError('power-of-two shape')
    levels=(leaves//roots).bit_length()-1
    driven=[i for l in range(levels) for i in range(leaves-(leaves>>l),leaves-(leaves>>l)+(leaves>>(l+1)))]
    assert driven==list(range(leaves-roots))
    return dict(NP=np,R=roots,leaves=leaves,levels=levels,node_count=leaves-roots,
                node_fault_driven=[0,leaves-roots-1],tied_zero=leaves-1,
                undriven=list(range(leaves-roots,leaves-1)),undriven_count=roots-1)

def root_rows(rows,root):
    if rows<0 or not 0<=root<128:raise ValueError('row/root')
    return sum((rows-1-(2*root+mb))//256+1 if 2*root+mb<rows else 0 for mb in (0,1))

def existing_return_storage(np=4096,roots=128,rd=64,rootd=128,rst=1):
    nodes=2*np-roots
    # Reuse pinned uarch_model_dsrom_return_prepare.storage formula atRST1.
    return dict(nodes=nodes,roots=roots,node_link_record_bits=65,node_valid_plus_record_bits=66,
       node_queue_bits=nodes*2*rd*65,node_output_alignment_lower_bound_bits=nodes*(65+1)*rst,
       root_input_queue_bits=roots*rootd*65,root_held_bits=roots*rootd*66,
       existing_declaration_lower_bound_bits=nodes*(2*rd*65+66*rst)+roots*rootd*(65+66),
       already_charged=True,bridge_must_not_recharge=True)

def buffer_price(max_rows,positions):
    if not 1<=positions<=6:raise ValueError('selected1..6positions')
    depths=[positions*root_rows(max_rows,r) for r in range(128)]
    record_bits=sum(depths)*69
    # Shared phase owner per physicalshard; no169bit owner per payloadseat.
    ptrs=sum(2*max(1,(d-1).bit_length())+max(1,d.bit_length()) for d in depths)
    control_bits=2*170+2+ptrs
    ff=unified_ff_um2()
    # R49 same-flop feedback repair:69bits*2.97umrowwidth, .27um cellrow;
    # two allowedBUF/bit included. .54um rowpitch is50pct allocation.
    raw_reserved=Fraction('2.97')*Fraction('.54')*record_bits
    return dict(max_rows_per_rank=max_rows,positions=positions,per_root_depth=depths,
       per_shard_seats=[sum(depths[:64]),sum(depths[64:])],logical_seats=sum(depths),
       raw_record_bits=record_bits,shared_owner_and_pointer_FF_lower_bound=control_bits,
       unified_FF_body_lower_bound_mm2=float((record_bits+control_bits)*ff/10**6),
       unified_FF_at50pct_lower_bound_mm2=float((record_bits+control_bits)*ff*2/10**6),
       R49_feedback_repaired_raw_record_reservation_mm2=float(raw_reserved/10**6),
       raw_record_reservation_per_shard_mm2=[float(Fraction(sum(depths[i:i+64])*69)*Fraction('2.97')*Fraction('.54')/10**6) for i in (0,64)],
       existing_576_capture_or_return_storage_credit_mm2=0,
       excludes=['read/write mux and comparators','codec/leases/arbitration','forward hold','clock/reset/PG/OBS/pin access','route/CDC/reverse-credit station state'],
       actual_slot_fit=False,mapped_area=False)

def phase_service(rows,positions,parallelism,gap_cycles=1,data_cycles=None,credit_cycles=None):
    if parallelism<=0 or gap_cycles<=0 or not 1<=positions<=6:raise ValueError('finite positive service')
    if data_cycles is None or credit_cycles is None:
        return dict(status='UNAVAILABLE_POSITIVE_PROVIDER_NOT_BOUND',exposed_cycles=None,F=None)
    if data_cycles<1 or credit_cycles<1:raise ValueError('positive forward/reverse mandatory')
    if parallelism==128:
        jobs=max(root_rows(rows,r) for r in range(128))*positions
    else:jobs=(rows*positions+parallelism-1)//parallelism
    return dict(status='CONDITIONAL_SUCCESSFUL_SERVICE_ENVELOPE_NOT_ACTUAL',
       words=rows*positions,parallelism=parallelism,required_issue_intervals=jobs,
       drain_if_all_payload_ready_and_all_grants_succeed_cycles=(jobs-1)*gap_cycles+data_cycles+credit_cycles,
       may_stall_phase_admission=True,field_internal_midphase_backpressure=False,
       actual_token_exposed_cycles=None)
