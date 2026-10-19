# N59-SAFE exact scatter candidate (safe2)

Owner-approved structural alternative; old m1 gate remains independent. SAFE=0
retains the legacy algorithm. SAFE=2 uses the same NU4/MCTX1 front/back contexts,
S-QWCOL rst_q x8 and formatter eb_r x16 base; replaces Q payload flops with SRAM.

## Model and physical cost

The interface accepts eight arbitrary FP32 seats per edge. One 1R1W 32x512 array
cannot provide eight independent row writes. Eight masked writer arrays plus a
1536-bit latest-owner table implement that exact contract without arbitration.
Logical Q payload:16384b; physical SRAM capacity:131072b. Each generated macro is
167.4x76.14um, 12745.836um2; eight total101966.688um2. They are real black-box,
LEF and SS/TT/FF compiler views with bit masks and read-before-write behavior.
The guide260x260 outline cannot contain those macros. Provisional518.4x648 has
2 columns x4 rows of macros on43.2um origins, horizontal gaps48.6um, vertical
gaps53.46um. Final outline/std utilization waits for synthesis area; do not call
this a synthesis-sized50% tile yet. Standard cells have a full-width southern
band and the channels. No area or token-rate credit is claimed before closure.

## Cycle and root contract

Q controls first capture at the face; SRAM read and kept one-hot owner select
capture on the next edge. Compiler prefetch advances1 edge. Same-edge write
forwarding preserves the logical flop bank read at that addressed edge. Unit bench checks17928 seats including arbitrary
scatter, duplicate highest-writer priority, retained lanes, clear/warm reset,
consecutive writes and same-edge read-after-write. Wrong-owner MUT7 must fail.
Native NU1 and MU14-op overlap benches measure the external edge contract.
The formatter SAFE path adds one internal lane encode/decode register stage;
its compiled output word slots remain fixed. Last-write-to-slot legality must
be established by the source-pinned native benches (no slot may move silently).

Regional scalar ports:ck core IO/context/codec/owner, ck_fmt formatter,
ck_qbuf eight raw SRAM clocks. All are sibling1:1 fixed-phase PLL roots.
The kit uses related_same_frequency and ordinary SS setup/FF hold timing on
all crossings: no data false paths or multicycle masks. Existing input/output
capture registers alone are not asserted to satisfy a four-slot LAND contract.
This <1mm tile is eligible only if linked root references and pin-flop spreads
measure <=80psTT+FF; a failed reference mismatch requires four-slot fixed
landings and a priced schedule change before adoption. Die must bind new roots.

## Mandatory SAFE checklist

1 Pins:existing every-pin p_* capture/output registers retained; reset lands in
  two face stages then eight kept copies. SRAM read/select is at the Q pin edge.
2 Reach:provisional outline<1mm; longest actual register/macro wire PENDING gate.
3 Fanout:existing reset/eb copies retained; gather owner onehot bits kept,
  each drives32 data bits. Scatter address/clear fanout PENDING synthesized lint.
4 Depth:formatter encoded lane addresses registered before constant-seat mux;
  Q32:1 payload flop mux removed. TT depth PENDING synthesized gate.
5 Storage:FIXED:16kb Q payload now8 masked SRAMs; owner1536b, seen512b remain
  control state; no indexed payload flop array in SAFE elaboration.
6 Floorplan:macros on43.2 lattice, channels>20um, full-width cell band available;
  pins spread full N/S/W faces (<6/um by aggregate plan). Measured area, fences,
  cell-band density and root mass placement PENDING gate/layout review.
7 Clock:3regional roots, actual macro references (clkqTT317/SS398/FF266ps),
  related ordinary STA, io hold0.03. Insertion/spread/reference PENDING gate.
8 Schedule:static, no backpressure; external edge preservation must PASS native
  production benches. Further LAND/outline changes handed to die/compiler lead.

This is a critical-prefix tile. Do not submit or write REVIEW.json: send PNGs,
area/fanout/depth/clock metrics and this checklist to the coordinator first.

## STRICT successor SAFE2 (safe1 is diagnostic only)

All Q controls first capture in p_qs/p_qb. SRAM read, coverage and owner
select then capture on the next edge; q_read_valid/beat align the consumer.
Compiler must ADVANCE input q_slot/q_slot_beat1 edge, retaining CMD and every
TX record slot unchanged. Native benches independently advance only the new
DUT prefetch; late-prefetch mutant keeps old inputs and must FAIL.

Producer law:raw DD capture+1, SRAM commit+2; prefetch pin capture+1 and
SRAM read+2. Sameedge forwarding permits read==commit. Thus each beat's
prefetch raw edge must be >= its last raw DD producer edge. AcceptedCMD
already requires all512 seats committed before request; if prefetch>=CMD
edge (oldQSLOT>=CMD+1), this is conditionally sufficient. This RTL proof
is not a production-image certificate. sysface_ovl owns failclosed compiler
q_prefetch_advance=1 plus explicit producer-ready metadata. Production GEN
readiness bounds and slot collision checks remain REQUIRED before binding.
The raw face replicas now first capture kind/mask/context bits, then decode;
no pre-register decode in the functional SAFE2 scatter path.

Native elapsed output-cycle delta remains0 only under the earlier prefetch
contract; input read latency increases1. Throughput and token schedule claims
remain scoped to the committed bench until the production manifest passes.

## Committed scoped evidence (973aa1754)

Fleet Verilator5.050:SAFE2 positive PASS (33TX records, done214->215,
65embedding rows), MU overlap PASS (14ops/4users,533 referenceedges),
late-prefetch mutant FAIL245errors (only1CMD escapes, zeroQ records).
Witnesses results/rtl/mu_qwen_1018/n59_safe/safe2_*.log, source identity
safe2_sources.txt. Full negative-control refresh runs independently.
No physical closure or production readiness claim follows from these benches.
