# Qwen O4 physical composition proposal

Architecture review input; **not adopted**, no new RTL/model changes or physical run.
Base `9ac1d9be`. Exact source hashes and calculated interface widths are in
`results/contracts/qwen_physical_composition_proposal.json`.

## Current implementation versus model

The layer0 TB parameter G=6144 describes an intended execution width, not a passed
6144-group execution or a placed die. Its code/scale/VM/KV arrays are behavioral.
They supply synchronous one-cycle returns without finite macro banks, arbitration,
or wire delay. The collective uses FW512, LAT11, BPC_NUM3600 and behavioral storage.
Those configured latencies are assumptions until a composed physical service verifies them.
Reduced exact gates and runtime-composition equivalence cannot close that physical gap.

Current matvec INT8 decodes signed8-bit codes to BF16 and uses existing BF16
multipliers; it does not implement the model's local two-nibble shift/add array.
Any area/energy argument based on nibble arithmetic must be reconciled with actual RTL.
The code port is128bits/group while the decoded arithmetic input is256bits/group;
KV mode supplies512bits/group. Do not treat these widths as one interchangeable bus.

The literal full-width ports are:

| Boundary | G64 maximum bits | G6144 maximum bits | Current cadence assumption |
|---|---:|---:|---|
| INT8 code return |8192|786432|one synchronous issue/return each cycle|
| Scalar activation return |2048|196608|one32-bit element per active group per cycle|
| BF16 scale return |16384|1572864|one256-bit word per active output group; only last/K-complete outputs|
| KV operand return |32768|3145728|one512-bit word per group in KV mode|
| FP32 result |32768|3145728|masked valid groups/lanes; not necessarily full width each cycle|

These are interface maxima, **not sustained simultaneous demands**. The actual
issued address/enable trace must determine multicast, bank conflicts and occupancy.
The TB currently accepts each group read/write by direct array indexing, and therefore
cannot prove that its VM has the necessary physical ports.

## Timing contracts that must survive physical composition

`ot_hdc_matvec.sv` documents memory return c+1, capture c+2, conditioning c+3,
product c+8 and sum c+13. The scale request is deliberately early: one-cycle scale
return is aligned to the split-tree output; the FP32 scale multiply adds five cycles.
An inserted ROM-capture or network stage must delay control, operands, valid, last,
address and scale metadata together. Adding an unmodeled physical register would
silently invalidate this cycle contract.

The runtime compilation owner's current simulator preserves the MAC and fixed-order
reduction RTL, adding no architectural queue. That is a verification technique, not
hardware compute sharing. Parent reductions, local fanout and register placement
still require physical implementation.

## Proposed smallest repeatable neighborhood

Start with **four groups ×16 output lanes** (1536 such logical neighborhoods per
G6144 die). This is a physical experiment unit, not a final capacity allocation.
Keep512codebits/cycle local,128activationbits/cycle local, and up to1024scalebits and
2048resultbits within the neighborhood. Macro capacity and output packing may require
multiple nearby ROMs; no inferred macro count is approved.

Placement contract:

1. Group code/scale macros and capture registers; orient output pins toward consumers.
2. Place signed-code conversion/product stages immediately beside captures.
3. Place accumulation and the first reduction stages beside their producing MACs.
4. Route higher reduction levels hierarchically, preserving the exact existing order.
   Budget each level's wire and logic against its existing register boundary.
5. Place destination VM banks beside output capture; use trace-proven banking or
   explicit arbitration, never an unbounded many-port behavioral memory.
6. Reserve peripheral HBM/collective landing regions and registered channels. Keep
   local code movement out of those channels.

Root must approve the fixed geometry, clock margin, loads, macro views and edge
budgets before routing. The max allowable wire+logic delay is clock period minus
launch clock-to-Q, capture setup, uncertainty and skew budget. **Do not invent a
numerical wire allowance before those quantities are supplied by the chosen libraries.**
Any extra stage changes execution latency and must re-enter the program/resource model.

## Existing physical warning

The source-pinned32-product-lane macro shard is NOT_MET at global route. Its report
has ROM clock-to-Q794.62ps and post-ROM-to-first-register data delay1333.16ps,
ROM path setup slack−1218.18ps; the report identifies no full O4 reduction tree.
It is not the final proposed neighborhood and does not prove all newer candidates
fail, but it demonstrates that synchronous behavioral ROM return is not yet a
physically validated one-cycle contract at0.92ns. No die clock can be inherited
from this small shard or from separately routed arithmetic.

## Critical acceptance order

1. Capture actual ME address/enable/scale/result traces for real layer0 instructions.
2. Bind those traces to a finite local memory allocation; assert no conflict or account
   for explicit stalls. Include HBM comparator service and collective dependencies.
3. Implement and route one neighborhood under fixed loads; check extracted setup,
   hold, slew, power connectivity and pin access, not just placement slack.
4. Compose two neighborhoods and their actual reduction/VM traffic; check exact
   data and cycles under finite queues and backpressure.
5. Only then replicate with die-level clock/power/routing and capacity accounting.

The biggest architectural gaps are finite VM/scale ports, actual ROM capture latency,
reduction-network physical reach, and all-client HBM service. Simulator compilation
progress addresses the ability to verify those gaps, not their physical resolution.

## First finite-bank trace check

The execution owner exported24 synthetic differential cases:22,080 group rows,
5,520 iterations (including frozen-clock iterations), four groups each. Excluding
frozen edges gives5,208 transaction cycles. This is **not a checkpoint trace**.
The compressed trace is retained with its SHA in the result record.

The candidate four modulo-word VM banks fails **192 read-port checks**: distinct
words address the same single-read bank in one edge. Thus the current candidate
cannot preserve the simulator's original cycle schedule. Code/scale depths and
ports passed this supplied subset. No route is authorized on this incomplete VM cut.
The root must choose trace-compatible skew/broadcast/replication or explicit stalls;
real checkpoint coverage is required before selection. We have not silently inserted
arbitration into the reported execution timeline.
