# HBM six direct station source candidates

`tools/hbm_b2/direct_stations.py` materializes a caller-declared full-width
pipeline on an exact direct source-to-sink mapping. Disabled output is byte
identical. Enabled mode checks every bit of the selected source and sink
slice and their one-bit clock identity, then rewrites only that sink slice.
All source outputs and other consumers remain connected as before.

Current source: intel1:/srv/opentallas-scratch2/claude/codex-hbm-bind-0300/top_native.sv,
379 native instances. Exact link ranges came from TOK-HBM `4fea3d46b`.
Generated candidate: intel1:/srv/opentallas-scratch2/claude/codex-hbm-direct-station-0822/top_six_stationed.sv.
The older top_station3.sv file in that scratch directory is superseded; use
the six-path candidate and this contract.

| Actual source | Sink port slice | Width | Source stages 0 -> candidate | Reset control bits |
|---|---|---:|---:|---|
| vmb_NW4.rr1 | hb_dbk_NW.rr[1284:1028] | 257 | 3 | valid[256] |
| vmb_NE7.eg | hb_vms_NE.bk_eg[2207:1932] | 276 | 6 | valid[275] |
| vmb_NE7.pr | hb_vms_NE.bk_pr[2127:1862] | 266 | 6 | valid[265] |
| vmb_NE7.status | hb_vms_NE.bank_status[143:126] | 18 | 6 | all 18 |
| vmb_NE7.xq2_done | hb_vms_NE.bk_xq2_done[7] | 1 | 6 | done[0] |
| vmb_NE7.xq_done | hb_vms_NE.bk_xq_done[7] | 1 | 6 | done[0] |

Cost: 4,143 FFs, comprising 135 synchronously reset control FFs and
4,008 resetless data FFs. The reset expression is the source bank's existing
`native_required__vmb_*__rst_n[0:0]` caller input. Its die delivery is not
qualified by this source change. Stable FF names and reset masks are in
receipt.json. No top-level pins or epoch signals were added.

Checks: a 4,096-cycle, 257-bit streaming lockstep with wrong-stage and
wrong-bit controls; all six actual-width/depth/control-mask combinations
over random streams and repeated warm resets, each with wrong-stage,
wrong-bit, and missing-reset mutants (18 caught). Data keeps shifting during
reset. Disabled identity, direct-map mismatch, clock mismatch, repeat
insertion, invalid depth, serial_k2 and runtime adoption refusals also pass.
Three focused tests pass in 3.76 seconds; no RTL array, physical build, route,
or full-system simulation was run. Actual native graph comparison confirms
exactly the six listed sink ports change and all unselected bits and all
other instance ports remain unchanged.

This is source preparation. Native links currently have zero source
registers; the prior plan's 2/5 stages were not existing source hardware.
The source adds 3/6 cycles, whereas the proposed geometry event adds one
cycle relative to those earlier planned depths. The parent compiler must
price the actual source composition. NE fullwidth_k1 requires its parent
corridor/capacity decision; the disproved serial_k2 form is rejected here.

NW DMA's RR_RT=80 compares all eight returned bank-valid bits and a common
landing tag. An isolated bank4 delay cannot be adopted as a complete fix.
The remaining request/response paths and padding to the common return edge
must be materialized coherently. The exact 16 current DMA groups are in the
HBM bind owner's dma_native_edges.json; no padding count is invented here.
`runtime_adopt` is rejected, and every receipt reports physical, token,
reset-delivery and parent-budget qualification as false. Parent plan,
placement, reset, compiler and token gates remain open.

## 128 North-role VMS source paths

TOK-HBM's source-defined `vms_128_pipeline_contract.json` was applied to the
same actual native source. The result is staged at
intel1:/srv/opentallas-scratch2/claude/codex-hbm-direct-station-0822/top_vms128_stationed.sv;
the complete contract and per-stage receipt are beside it as
vms128_contract.json and vms128_receipt.json.

All 128 selected native source/sink bit ranges match. An independent graph
comparison retains all 379 original instances, masters and parameters,
changes exactly 93 sink ports, and preserves every unselected sink bit and
other instance port. Cost: 176,798 FFs, including 3,074 reset control FFs;
pipeline depths are 2 through 31. Representative request width 17 and
PQ width 285 at depths 2/31 join the six original miter cases, with 27
wrong-stage/wrong-bit/missing-reset mutants caught. Three focused tests
complete in 3.94 seconds.

The 128 candidate supersedes the five NE7 VMS paths in the six-path source;
they must not be inserted twice. NW4 DMA rr1 is outside these 128 VMS paths
and still belongs to its complete eight-bank DMA return bundle. The missing
128 South-role paths have no qualifying geometry and are not fabricated.
Parent calendar dates, physical capacity, clocks, reset delivery and die
qualification remain open. The source adapter explicitly rejects requested
runtime adoption and serial_k2, and checks caller-declared connected widths
against the actual source before generating any candidate.

## All 16 DMA legs and combined 144-path source

The source-guided DMA geometry worker reconstructed all eight actual
17-bit request and 257-bit response legs using current D18 pin files.
Those pin ABIs are already correct: the 137/258/2064 widths and reversed
rows were stale internal-station metadata. The authoritative North DMA
core is `u_hb_dbk_Q__q1`, resolved from actual bindings. No epoch was added.
The geometry/count preparation reports all 2,192 pins, no missing/surplus
pins, maximum per-bit hop 362.88 um, and no station centre inside any of
159 core bodies plus 4.32-um halos. Full per-bit FF body packing is still
required. The independent geometry worker owns its diagram/review and
plan event; this adapter does not route anything.

Request and return station counts per bank are each
`[17,20,15,16,5,8,3,6]`, including the two explicit endpoint stations.
These 16 source paths add 24,660 FF bits, with 180 reset control bits.
`dma16_contract.json` materializes their actual source slices. The combined
VMS128 + DMA16 candidate is staged at
intel1:/srv/opentallas-scratch2/claude/codex-hbm-direct-station-0822/top_vms128_dma16_geometry.sv,
with combined144_contract.json and combined144_receipt.json alongside.
All 379 native instances/masters/parameters remain unchanged; 144 paths
rewrite 102 sink ports and preserve every other port and unselected bit.
Total source FF cost is 201,458 bits, including 3,254 reset control bits.

The eight unpadded DMA return budgets FAIL their common RR_RT=80 date:
they require an additional `[39,33,43,41,63,57,67,61]` cycles. The budget
uses request pin launch to response pin launch, with intrinsic latency 7
from the actual-bank component measurement and controller RTL contract;
the consumer captures one edge later. A budget helper publishes both
options without selecting either: request padding costs 6,868 FF bits
and changes the bank read sample dates, requiring a compiler memory-version
calendar; response padding preserves those sample dates but needs
103,828 buffer bits and each bank exceeds the 2-kb SRAM threshold. The
current dated calendar has no qualified immutable-read window, so no
padding or runtime adoption is selected. The combined source remains
preparation and explicitly reports `qualifies_parent_budget=false`.

Five focused tests pass in 3.92 seconds. Separately, one bounded Yosys
proc/opt of the exact emitted 128-path station glue (upstream cores are
arbitrary inputs) retains exactly 173,724 resetless `$dff` bits and 3,074
synchronous-control `$sdff` bits. This establishes emitted-state retention
without a full native core elaboration or physical mapping. That job is
terminal at intel1 codex-hbm-direct-station-0822/station_scope.*; no
physical source gate or token pass is inferred.
