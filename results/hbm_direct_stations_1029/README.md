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
