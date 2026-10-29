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
