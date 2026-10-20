#!/usr/bin/env python3
"""Source-conditioned analytical timing, not a native-clock or reset qualification."""
import json
D, K = 4, 2
T = 833.3333333333334
rows=[]
for shift in range(-3,4):
    phi=shift/4
    rows.append(dict(phase_T=phi,write_to_capture_ps=(K+phi)*T,
                     capture_to_overwrite_ps=(D-K-phi)*T))
print(json.dumps(dict(status="MODEL_ONLY_HOLD",period_ps=T,depth=D,K=K,
 assumptions=["same-rate clocks, fixed measured relative phase phi", "source write_oh and destination read_oh epochs correspond", "one reset epoch is established before first valid input", "no clock stops or epoch slips in active execution"],
 ownership="slot s is written only when write_oh[s]; selected only when read_oh[s]; each recurs every D edges",
 budget="data slot q -> read o d only: cq+wire+comb+setup+uncertainty < (K+phi)*T; hold must precede next overwrite",
 rows=rows, min_sample_age_ps=min(x["write_to_capture_ps"] for x in rows),
 min_overwrite_gap_ps=min(x["capture_to_overwrite_ps"] for x in rows),
 sdc_scope_problem="current wildcard endpoints include writer valid/selector/control; per-cone ownership and first-use proof missing",
 reset_problem="writer rq adds one reset stage beyond record depth=3 flat reference; stopped-clock reset cannot be inferred from synchronous pads",
 storage=dict(crossings=26,payload_bits=952,bank_bits=3808,read_output_bits=952,chunks=56,max_independent_ring_bits=748,source_declared_state_bits=6608,record_landing_flops=5936,assertion_epoch_bits=672,
 note="logical crossing objects are <=748 bank bits; total3808 real bank bits must be charged, chunking is fanout implementation, not storage exemption")),indent=2))
