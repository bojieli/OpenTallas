Distributed native RESULT548 source
=================================

`qkd_result_node` is the producer-local physical master; instantiate B=8*h+b
next to the corresponding actual `ot_qwen_tp8_pv_join16_static` source. Connect
that source's independent out_valid/out_epoch/out_data, never the finalizer's
aggregate aliases. Feed each node the same CMD event and epoch/layer that starts
its producer. The node retains layer/epoch on that event and captures the actual
512-bit result at CAPTURE_AGE. A changed later command bus cannot retag it.
Record bits match qkd_native_attention_record exactly:
{reserved5=0, kind4=RESULT3, layer6, epoch16, beat5=B, data512}.
The local result register is already encoded; no central 16384-bit data bus or
32-way result mux is synthesized by these masters.

Eight nodes form each stack's registered path. Injection replaces the otherwise
forwarded 548-bit upstream record only on a compiled slot. A collision faults;
there is no arbitration, credit, ready, queue occupancy or arrival-driven delay.
Two pair merges then one root merge form a balanced four-stack merge near link.
Every merge is an independent registered two-input master. Valid disagreement
with the compiled slots faults; it never shifts another record into the slot.
Faults are sticky until reset and must join actual native STATUS fault data[2].
Faults do not themselves define an exceptional retry policy.

Analytical component sizing before physical build:
- 32 producers x 512 bits = 16384 payload bits/context (512 FP32 words).
- Retention: 32 x 548-bit records, plus 32 x 548-bit hop output registers.
- Each registered boundary carries 548 record bits + valid; 35 clock entries.
- Three merge output registers carry another 3 x 548 bits. No SRAM required.
- Each stack carries eight records/context; root carries 32 consecutive cycles,
  peak 512 payload bits/cycle and 548 physical record bits/cycle.
- Local clock/control/age identity register overhead is explicit in RTL.
  Counters are 32-bit to accept the actual compiled service ages.
- This is a source decomposition, not an area, route-track or slot-fit estimate.
  Parent must assign 32 source homes, registered links within measured reach,
  3 merge rooms, pin faces, clock insertion/phase, and add every real hop to the
  compiler calendar. Longer geometry needs more actual register masters/ages.

Schedule convention: on a node's CMD edge age resets to zero. The first edge
AFTER CMD evaluates age=0. CAPTURE_AGES has one 32-bit value per node. STACK_FIRST
has one 32-bit stack-output age per stack. Node n injects at
STACK_FIRST[h]+2*n-7; it traverses 7-n registered downstream nodes and appears
at the stack's output at STACK_FIRST[h]+n. Two merge registers put it on the
root output at STACK_FIRST[h]+n+2. Every injection must follow its capture.
The wrapper requires the four stack windows to be consecutive eight-edge
windows, and all node/merge CMD age origins must correspond to the same service
context. Different qualified clock phases must preserve the compiled sampling
edges; clocks are exposed individually, no clock-domain crossing is claimed.

Default CAPTURE=8, FIRST={32,40,48,56} are a component bench fixture ONLY. They
are deliberately unrelated to actual QK/PV/HBM latency. No source-derived full
kernel calendar or actual producer arithmetic is qualified by this test.
`run.sh` uses real RTL in Icarus: 32 full records in each of four consecutive
contexts without reset, changed command buses after CMD, exact metadata/payload
comparison, and missing/duplicate/early/stale faults. A producer-local data
mutant must fail the exact comparison at beat17. Bench clocks are equal phase.

Physical qualification, actual finalizer wiring, real CMD/HBM/PV calendar,
production throughput price, and complete token execution remain open.

Actual arithmetic wiring successor
---------------------------------
`qkd_result_finalize_collected` instantiates the actual static finalizer from
commit 385bc2d8b, with additive independent node_valid/node_epoch/node_layer
outputs. Its 32 actual join16 producers capture layer on the same local start
edge that captures epoch, and publish that held identity alongside arithmetic
results. The collector checks both actual producer epoch AND layer. Aggregate
out_valid/out_epoch remain for compatibility and are unused by collection.

The wrapper preserves all 32 join clocks and uses each same clock for its
producer-local collector. It accepts no credits or ready input; the legacy
finalizer's out_ready is tied available and its ready outputs are observations
left unused. Three independently exposed merge clocks still need qualified
sampling phases. CONFIGURED defaults to zero and simulation fails closed.
Compiler CAPTURE_AGES and STACK_FIRST default zero and must be supplied.
Capture ages must equal the actual finalizer expression
max(P0_AGE,P1_AGE,R_AGE)+ADD_LAT+MUL_LAT+2 under the stated age convention.
This source equality is checked for every producer independently.

`run_actual.sh` elaborates and runs ALL 32 actual 16-lane ADD7/MUL6 producers,
not substitute arithmetic or aggregate valid aliases. It compares 1024 FP32
words in two consecutive contexts through final RESULT548, including command
bus changes after start. Its fixture P0/P1/R=8/20/48, capture63, stack windows
80/88/96/104 exercise source wiring only. They are NOT the source-derived
whole-service QK/PV/HBM or physical clock calendar.
