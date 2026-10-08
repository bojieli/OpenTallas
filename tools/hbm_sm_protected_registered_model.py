#!/usr/bin/env python3
"""Architecture sizing, before CE owner/transaction-shell RTL.

This candidate is NOT ready for adoption: the final consuming-edge storage
check and complete ingress CE census are explicit implementation obligations.
"""
import json,math

def model():
 inp=dict(run=82,mem_response=66,allocation_response=50,x_response=2077,publication=17,arrive_toggle=1,sticky_sm_fault=1)
 out=dict(mem_request=33,allocation_request=41,x_request=32,descriptor=57,start=48,x_write=2063,done=1)
 # Original mapped dual-owner result is evidence, not a prediction of successor map.
 baseline=5343
 protected_mailbox_payload=2*(sum(inp.values())+sum(out.values()))
 chunks=math.ceil((2572+sum(out.values()))/32)
 groups=math.ceil(chunks/8)
 return dict(status='architecture_candidate_before_RTL',admitted=False,replicas=32,
  baseline_dual_owner_mapped_bits=baseline,input_mailbox_bits_per_copy=inp,
  output_escrow_bits_per_copy=out,duplicated_mailbox_payload_bits=protected_mailbox_payload,
  preliminary_state_lower_bound_bits=baseline+protected_mailbox_payload+chunks+groups,
  additional_state_unpriced=['protected mailbox occupancy/epoch IDs/actual-consumption receipts','mailbox SECDED/local final checks','complete ingress/credit queue CE census','phase controller protection'],
  epoch_edges=8,maximum_core_logical_steps_per_edge='1/8',
  phases=['0 capture immutable input-mailbox and actual-output-consumption receipt snapshot',
          '1 input protection chunk checks, no core or endpoint side effects',
          '2 input check reduction; failure latches abort',
          '3 advance BOTH complete cores once under synchronous CE using verified snapshots',
          '4 capture dual output intent and complete owner/ingress state observation',
          '5 register equality of <=32-bit chunks; payload checks qualified by captured valid',
          '6 register reductions of <=8 chunk verdicts',
          '7 final verdict permits output escrow export; endpoint consumption produces a held receipt'],
  channels=dict(input='one protected finite mailbox per input; capture only with actual ready, hold until verified core step consumes it',
   output='one duplicated escrow per output; retain pending identity across core logical cycles; issue once, hold under backpressure, return actual receiver-consumption receipt',
   descriptor='core d_ready is actual south-consumed receipt, never local escrow capacity',
   start='core start_ready is actual native start consumption receipt; prevent duplicate issue',
   xwrite='one committed pulse per logical xw_en event, never repeat level while core frozen',
   arrive='capture stable toggle with outstanding-operation identity; cannot count it twice',
   fault='sticky abort suppresses all external effects; cold POR only'),
  compare_chunks32=chunks,compare_groups8=groups,
  latency='at least8 edges per old logical core cycle; output publication and returned consumption can add epochs; exact gate must measure full13-record6448-X trace before model adoption',
  physical='one clock with synchronous CE on EVERY sequential core/helper bank; no combinational clock AND, no SDC-only relaxed domain',
  critical_unsolved=['A registered verdict alone does not protect a payload corrupted after verification. Output escrow must retain independently protected copies and provide a qualified consuming-edge check or an explicitly checked downstream capture; do not simply delay valid.',
   'All ingress helper state including uninitialized valid-qualified FIFO payloads must enter the CE/protection inventory. Existing owner-only parity is insufficient for this rewrite.',
   'Final reduction, local output checks and actual protected mailbox implementation still require SS/FF +15ps/DRC0 and duplicate-bank mapped preservation.'],
  next_implementation='generate CE-enabled distinct owner+ingress+channel successor hierarchy; implement protected input mailboxes and output receipt escrow; qualify consuming-edge protection before exposing outputs')
if __name__=='__main__':print(json.dumps(model(),indent=2))
