# DS-ROM combined-lever L20 bench (CLAUDE DS-INTEGRATION, 2026-10-05)

One DeepSeek-V4.1 L20 layer stage (position 1,048,575, rank-0 die) with every adopted-or-exact recovery lever ON
together, against the golden, as a lever matrix. Driver: `tools/dsrom_combined_l20.py`. Plan as executed:
`run_plan.sh` (ot-epyc2), with the field and su_norm runs moved to ot-pve1 when EPYC2 load passed the admission
threshold. The joined record is `combined.json`. The tool exits nonzero on any mismatch, unresolved source
conflict or missing run.

No new simulator. Each lever's own bench runs unchanged from one pinned snapshot (`SOURCE_COMMIT` + the LA6
su_norm overlay). A unit whose committed record pins RTL that is current in the snapshot is not re-run (owner
rule 2026-10-06: no same-source replay). Its committed L20 rows are collected instead, and `static.pin_currency`
is the proof.

## What a per-unit bench cannot check, and what this bench adds

| Check | How | Result file |
|---|---|---|
| Every configuration of the matrix elaborates one definition per module | Module-body hashes over each configuration's source union (each ON lever's sources, plus the 0.9 GHz SU for any OFF SU node, plus the field vehicle) | `static.json` |
| Lever records measured on RTL still current | Each record's `source_sha256` / `rtl_sha256` compared with the snapshot | `static.json` `pin_currency` |
| Two lever records claiming one composition node | Node ownership over `levers/*.json` | `static.json` `composition_node_claims` |
| Chained exactness of the fused units on the L20 stage | Golden L20 producer output bits == consumer input bits on every edge between fused units. Exact-alone units on equal operands are exact chained. Negative control: one flipped bit must be caught | `edges.json` |
| Field spine × q-element | The v9 spine vehicle with the DS q-element on its FP8/FP4 pairs (pair FILE SWAP `rtl/v41die/swap/ot_v41_pair_pq_w17w10_qelem.sv`), every L20 phase × region and every node back to back, against the same vehicle without it | `field_pq0*`, `combined.json` `field` |
| PQ × q-element | Must not be buildable. The q-element has no PQ shadow configuration, no row op tag and no segment-tree op parity | `combined.json` `field.pq1_q9` |
| The matrix in the timing authority | `tools/dsrom_1m_allmeasured.compose` on its own adoption path (`apply_levers`): all-OFF, all-ON, each lever alone, all-ON minus each | `compose.json` |
| Run vs composition | Unit L20 cycles vs the composed node values; field PQ 0 fresh vs the committed v9 baseline; q-element vs W10 element on the v9 spine | `combined.json` `run_vs_composition` |

`deferred_input_hold.json` lists every fused unit whose routed closure left data-input hold (or all IO timing)
to the parent. The S81 full-die re-run (plan item 10) must check those boundaries.

## Result (2026-10-06, record verdict PASS, tool exit 0)

Snapshot: `SNAPSHOT_OVERLAY.txt`. The lever records are refreshed from main 29f36e8b0, where su_norm (LA6X) and
su_swiglu are ADOPT. Run logs: `MANIFEST_epyc2.txt` and `MANIFEST_pve1.txt`.

**Exactness at L20 with every lever ON (all bit-exact, 0 mismatches)**

| Unit | L20 cases | Source of the rows |
|---|---|---|
| su_hcpost | attn and ffn hc_post, 103 cycles | Committed m5a5 run; RTL pins current |
| su_norm, LA6 core | attn and ffn hc_pre_norm 321, q_norm 285, kv_norm_rope 279 cycles. Full lane count, with RTL FP at N 64 | Fresh run on PVE1 (35 cases) |
| su_norm, adopted LA6X (RXS, SXC, FREG) | hc 323, q 287, kv 282 cycles | Committed `su_norm/measure.json` from today, every case including L20; all 24 pins current |
| su_swiglu | swiglu 240, shared 190, z_quant 76 cycles (W 64 RTL) | Committed r4; pins current |
| su_softmax | T640: max 93, exp 148, den 50, sink 14, normalize 131 cycles | Committed r2 e54; pins current |
| su_routeract | die L20: impl 0 224, impl 1 132 cycles | Committed sim.json; pins current |
| Field v9 spine, PQ 0 | 11 L20 nodes (two of them on two dies), 3,008 phase×region runs plus node back-to-back runs | Fresh run. Measured cycles equal the committed v9 baseline on every node |
| Field v9 spine, PQ 0 + q-element QX 9 | Same 11 nodes, every run exact | Fresh run. **This combination had never existed in RTL** |
| Field v9 spine, PQ 1 | L20 nodes exact | Committed v9 `field_pq.json` |
| Field v9 spine, PQ 1 + q-element | **Not buildable** | Structural negative control |
| L20 data edges | 12 of 12 equal; flipped-bit negative control caught | `edges.json` |

**Matrix (tools/dsrom_1m_allmeasured, position 1,048,575)**

| Configuration | AR µs | AR tok/s | MTP tok/s | L20 on the critical path, µs |
|---|---|---|---|---|
| all-OFF | 620.078 | 1,612.7 | 4,773.2 | 24.534 |
| all-ON (field_spine_pq, hcpost, routeract, norm, swiglu, softmax) | 414.834 | 2,410.6 | 6,568.9 | 18.615 |

The single-lever and all-ON-minus-one rows are in `compose.json`. Summed alone, the six levers save 205.040 µs;
together they save 205.244 µs. The +0.204 µs difference is the measured CDC that drops between adjacent fused
nodes. **No negative interaction.** All-ON is not physically qualified: su_softmax, field_spine and
field_spine_pq are still PENDING_SSFF.

**Findings**
1. **The q-element and the PQ spine cannot coexist.** `ot_v41_pair_pq_w17w10` had no q-element path, and the
   q-element has no PQ shadow configuration, no row op tag and no segment-tree op parity. To combine them, the
   q-element's owner must port `ot_v41_elem_pq_tags` and the tag/parity mechanism into
   `ot_v41_rom_elem_qx_w10`, then re-route. Until then the composed all-ON field (PQ spine) assumes the W10
   element.
2. **The q-element changes L20 field-node cycles, and nothing composes this.** On the v9 spine (PQ 0, same
   harness) the deltas are: a_proj +8, wo_b +5, wq_b +11, shared_gu +8, experts_gu +28, down +31 cycles;
   cmp.wk, wo_a and router are unchanged. That is +91 cycles over the L20 field nodes. No lever record or
   composition carries the q-element, so these deltas are UNVALIDATED in the published rate.
3. **Wire-stage count is stale.** The field_spine and field_spine_pq records charge 80 S81 wire cycles per field
   phase. The current `dsrom_s81_fulldie_20261004/floorplan.json` gives 78, so the levers are conservative by
   2 cycles per phase.
4. **su_softmax lever record is 1 cycle low on two nodes.** It carries attn.max 92 and attn.normalize 130
   cycles. Its own current exact run (r2 e54) measures 93 and 131. That is +0.0017 µs per occurrence.
5. **Main had no source for the measured lever, now resolved.** When this bench started, main's
   `rtl/hdc/v41x/ot_dsrom_su_norm.sv` was the pre-LA6 version, and the measured LA6 lever existed only in
   `su_fusion_takeover/la6_inputs/`. Main now carries LA6X.
6. **The field `--qelem` build was broken on main.** `tools/dsrom_1m_field.py --qelem` listed two QX10 files
   that are not on main (`ot_v41_chain4.sv` and `ot_v41_fadd2.sv`). Fixed by keeping only the sources present.
7. **A mixed die needs one shared FP-wrapper file.** Any configuration with some SU levers ON and some OFF has
   both `ot_hdc_fastfp_lat.sv` and `ot_hdc_fastfp_lat_f12.sv`, which define the same modules. The die must
   name the f12 file die-wide. At every ALAT and MLAT the baseline SU instantiates, its latency is identical and
   its output is bit-exact (c464d70f1).
8. **Five CDC crossings remain on fused nodes**, about 0.025 µs per layer. Their dependencies stay at 0.9 GHz:
   hc.sinkhorn feeds hc_post, hc.pre_post feeds hc_pre, and ffn.weights feeds route_w.
9. **The golden's mix order is lagged.** A block's hc_mixes yields the pre weights for the NEXT block
   (`hdc_golden_v41.Model.layer`). The L20 edges follow it.

## Reduced end-to-end token with levers ON: BLOCKED

None of the reduced DS vehicles carries any lever. Those vehicles are `rtl/hdc/v41/ot_hdc_core_v41.sv`,
`rtl/hdc/v41x/ot_hdc_core_v41x.sv`, the `sys_*` system gates and the wavefront stage. Their norm, softmax,
swiglu and hc_post run as ISA ops on `ot_hdc_v41x_vec` and `ot_hdc_v41x_sfu`, and their matvec on
`ot_hdc_v41_matvec`/`qe`. No PQ, QELEM or fused-SU path exists. The highest position the reduced vehicle
supports is **127** (`tools/hdc_isa_v41.py` POS_MAX 128, T_MAX 144 = 128 window + 16 selected).

To run that token, the fused units would need new SU ISA ops at reduced shape (dim 160), program-generator
lowering and core adapters. That is a vehicle build, not a run. No reduced-vehicle record has per-layer cycles
either. The levers' per-layer-type exactness at the target position (L0, L3, L20, L24 and the head, at
1,048,575) is in `units.json`.
