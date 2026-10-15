#!/usr/bin/env python3
"""Candidate physical decomposition of the actual V1 qslots, before RTL adoption."""
import json
from pathlib import Path

def model(npt):
    ns, nd, pwt, selw = npt+7, npt+13, 545, 4
    widths = [32]*17+[1]
    assert sum(widths)==pwt
    # Original output leaf captures all source payload and control before muxing.
    control_ff = ns+nd+nd*selw+nd+2
    original_output_ff = (ns+nd)*pwt+control_ff
    split_output_ff = sum((ns+nd)*bits+control_ff for bits in widths)
    original_capture_ff = ns*pwt+ns+1
    split_capture_ff = ns*(pwt+2)
    return dict(npt=npt,ns=ns,nd=nd,payload_bits=pwt,selw=selw,
        original_capture_ff=original_capture_ff,original_output_ff=original_output_ff,
        candidate_capture=dict(module='ot_hgi_coll_qslots_capture',params=dict(NS=1,PWT=pwt),
            replicas=ns,payload_and_slot_ff=546,sticky_fault_ff=1,
            actual_port_bits=2*pwt+6,proposed_outline_um=[21.6,103.68]),
        candidate_output=[dict(module='ot_hgi_coll_qslots_output',params=dict(NS=ns,ND=nd,PWT=bits,SELW=selw),
            replicas=17 if bits==32 else 1,
            ff=(ns+nd)*bits+control_ff,
            actual_port_bits=(ns+nd)*bits+ns+2*nd+nd*selw+4,
            proposed_outline_um=[25.92,103.68] if bits==32 else [25.92,25.92]) for bits in [32,1]],
        added_capture_fault_ff=split_capture_ff-original_capture_ff,
        added_output_control_ff=split_output_ff-original_output_ff,
        added_total_ff=split_capture_ff+split_output_ff-original_capture_ff-original_output_ff,
        added_logical_cycles=0,
        physical_clock_entries=ns+len(widths),
        parent_clock_pin_increase=ns+len(widths)-2,
        clock_delivery='Each leaf needs explicit same logical phase phi minus measured local insertion; new clock buses are a distinct parent ABI until adopted. No measured delivery/clock area claimed.',
        logical_contract='C source capture -> C+1 output-leaf ingress capture -> C+2 registered destination',
        bandwidth_bits_per_cycle=dict(source_payload=ns*pwt,destination_payload=nd*pwt),
        controls='Each output slice has identical compiler slots/selects; validity and sticky faults must agree across slices. Capture faults are OR of actual source-leaf faults.',
        physical_status='CANDIDATE ONLY: outlines are pin/cut estimates, not grants or measured routes; real clock entries, channels, fanout, all incident pins and total parent inventory remain OPEN')

def main():
    q3,q2=model(3),model(2)
    result=dict(scope='Current V1 structural qslots candidate only; no source replacement, physical view or performance qualification',
        source='rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_qslots.sv',
        candidates=[q3,q2],die_extra_ff=q3['added_total_ff']+3*q2['added_total_ff'],
        die_capture_replicas=q3['ns']+3*q2['ns'],die_output_replicas=4*18,
        physical_masters=5,die_added_physical_clock_pins=q3['parent_clock_pin_increase']+3*q2['parent_clock_pin_increase'],
        required_adoption='Explicit parent/physical clock ABI update plus source-exact positive/mutants and actual typed leaf grants. Do not silently replace current V1 or inherit control256 closure.')
    p=Path(__file__).resolve().parents[2]/'results/arch/hcoll_physical_1103/qslots_partition_model.json'
    p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
