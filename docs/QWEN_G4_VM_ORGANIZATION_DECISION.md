# G4 VM organization: finite-port alternatives for root decision

Proposed next cut: **eight XOR-skewed word banks, no read replication**.
For logical512-bit word `w`, bank=`(w ^ (w >> 2)) & 7`, row=`w >> 3`.
The mapping is bijective for all4096 words of a256KiB experiment allocation.
This is not a full-layer VM allocation (the layer0 TB contains177808FP32 elements).
Production capacity and all-client traces remain required.

## Measured requests, modeled bank assignments

The retained issued synthetic G4 trace has5208 nonfrozen cycles. We test actual
request addresses/enables; no fabricated issue sequence and no RTL edits.

| Candidate | Read-conflict cycles | Write-conflict cycles | Storage copies | Isolated extra service cycles |
|---|---:|---:|---:|---:|
|4 modulo wordbanks|64|128|1|320|
|4 modulo banks ×16 independent lane banks|0|128|1|256|
|4 skew banks (`w xor w>>3`)|64|0|1|64|
|4 skew banks,2 read replicas|0|0|2|0|
|8 skew banks (`w xor w>>2`)|0|0|1|0|

Extra service cycles are the sum of required serialization in this frozen trace,
not a re-executed program latency. A true stall changes dependent event timing.
The8-bank candidate has at most one distinct word read and one distinct word
write per bank per cycle on this trace, with no same-address simultaneous R/W.
No general workload guarantee follows from this synthetic coverage.

## Why lane splitting alone fails

Conflicting writes are to distinct words20,28,36,44 with overlapping/full lane masks,
not disjoint lanes of one word. Splitting each word into16 lane banks fixes the
observed scalar-read conflict but leaves four writes competing per lane bank.
The checker merges disjoint masks of the same word deterministically before port
counting; overlapping same-lane writes are rejected because the trace lacks data
with which to prove equality or define priority. The supplied trace has zero same-word
multiwrite cases, so separate positive/negative tests qualify that rule.

## Concrete macro/storage realization

Use32 `ot_sram_1r1w_512x128_m4_r2c2` macros: four128-bit slices per512-bit bank,
eight banks. Each macro has an independent synchronous read and write port and
128 bit write-mask inputs; a32-bit lane mask expands to its32bit positions.
Capacity:32×512×128bits=256KiB, no replication. Compare original4banks of two
1024×256macros: also256KiB but8larger macros. This trades greater banking/periphery
and steering for ports, not free capacity. Macro count does NOT equal area ratio.
The alternative4skewbanks×2replicas needs512KiB and replicated write distribution.

A read request that shares a word with another request is served once and broadcast
through the lane selectors. Distinct conflicting words are illegal at this experiment's
unchanged-cycle contract. Read return selects the requested32-bit lane from512bits;
write requests are demultiplexed by bank, merging only disjoint same-word lane masks.
The input XOR bank decode, request arbitration checks, lane selectors and response
steering must be placed/routed; no claim that they fit0.92ns without another cycle.

## Capture/latency boundary

Keep one synchronous macro read edge and the actual matvec mq_x capture. Keep
mq_wrom→s2INT8-to-BF16→s3→bmul/fadd and early scale request unchanged. Addedlogical
cycles=0 in this proposal; routed failure requires root-approved extra capture and
new numerical/cycle verification. HBM/SU/collective use is not in the supplied trace;
it cannot inherit free extra ports.

## Acceptance before route

1. Root approves8bank skew and experiment capacity.
2. Connect the selected macro models and real G4 trace harness, including nonzero data,
   lane writes, broadcast, randomized stalls and explicit read/write ordering.
3. Add actual checkpoint-issued and concurrentSU/collective traffic or retain narrow scope.
4. Approve placement and timing constraints with source-pinned macro LEF/Liberty.
5. Route the combined neighborhood only after these checks. No duplicate route started.

## Candidate hardware model acceptance

`rtl/physical/ot_qwen_g4_vm_skew_candidate.sv` instantiates all32 unmodified
physical SRAM models (including their real bit-mask and repair ports, repairs off).
The Icarus gate writes4096 complete words with distinguishable nonzero data and
checks16384 lane reads. It also verifies disjoint same-word mask merging,
same-address read-before-write, sticky fault, no modification on overlapping writes,
and explicit rejection of same-bank distinct-word reads. The wrapper suppresses
all requests atomically on an illegal conflict; it never picks a hidden winner.

Read address is sampled on a rising edge, macro output/selector registers become
visible afterward; the existing matvec mq_x capture would consume that response
on the following edge. This verifies macro behavioral latency, not extracted timing.
The full-capacity bank/row mapping is bijective. Production core hookup is absent.

Trace correction: the storedCSV now contains **direct pre-edge samples** from the
execution owner's revised harness; edge=1 samples are accepted, edge=0 ignored.
The prior file was post-edge, unsuitable for transaction timing alignment. The revised
trace reproduces the same conflict counts and candidate result; hashes are renewed.
No latency claim is taken from the old post-edge snapshots.

The macro harness also replays all5208 accepted direct-pre-edge trace cycles through
the32 actual SRAM models, with generated distinguishable nonzero write data and an
independent scalar-memory scoreboard. All reads match; no bank fault occurs. The
payload is synthetic, not checkpoint arithmetic. This proves the proposed bank
steering/masks and macro-model latency for the recorded addresses, not a core result.
