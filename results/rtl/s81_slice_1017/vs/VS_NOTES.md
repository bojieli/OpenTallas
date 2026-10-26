# vs: the beat-leaf SU lane engine (S81-SLICE-SU, 2026-10-17)

## Masters per beat leaf (each its own clock root, registered pins on both sides)

| Master | Content | Flops (yosys proc count, pre-opt) |
|---|---|---|
| `ot_s81sl_vs` | command decode, vp extension-port reads and writes, vq u stream, RB / QR / MOE lanes (8 x `ot_dsrom_qadd` 6, 4 x `ot_hdc_qmul_lat` 6), SW and RA sequencing | 9,404 (ORFS synth: 8,888 + 516 DFF), 8,131 um2 std cells |
| `ot_s81sl_vsw` | ONE hub SwiGLU lane `ot_s81_su_swl` (unchanged) + a 4-element serialiser / deserialiser; 2 x 128x256 SRAM wait lines | ~14k (the lane alone 14.1k) |
| `dsfd_su_t_rxsf` -> `dsfd_su_t_rxsb` | the closed hub RA lane pair (sqrt(softplus)), unchanged | 12.8k + 13.8k (hub CTS: 10.1k / 10.3k sinks) |

Why the split: one SW lane is ~14k flops, one RA lane ~27k, an adder or multiplier ~620. Four SW lanes (the read-port
limit) would be ~56k, so SW is one lane on its own root. RA reuses the two closed hub leaves.

**Decision for S81-SLICE:** router rows are 6 per slice, so the RA pair is needed in only ONE leaf per slice. vs always
has the ra_* pins, so either every beat leaf carries the pair (2 x ~11k-sink leaves x 80 = ~2M flops for 96 elements a
layer), or the compiler puts the router rows in one fixed leaf and the other four leaves get a pair as well (no tied
ports allowed). The cheaper structural option is a vs variant without RA pins for the four non-RA leaves.

## Ops (vp command ops 8..13, forwarded on s_v / s_d; one op at a time)

Measured on the bench (`tools/s81_slice/vs_bench.sh`, L0 and L2), from the vp command pin to the last vs result output:

| Op | Work in the bench | Cycles | Model |
|---|---|---|---|
| SW | 6 groups (24 elements), wb | 151 | 4 n + 127 |
| SW | 16 groups (64 elements = 2 act-quant blocks), wb + vq | 191 | 4 n + 127 |
| QB | 8 sub-beats (64 z values) to vq | 19 | n + 11 |
| RA | 4 router scores | 145 | n + ~141 |
| RB | 96 rows (384 scores + bias) | 115 | n + 19 |
| QR | 16 rows (one head's 64-element RoPE tail) | 57 | 2 n + 25 |
| MOE | 64 elements x 7 experts | 75 | 56 + 19 |

Rates against the SPEC lanes (per slice: SW 64, RX 2, QR 1, QB 2 blocks): SW is 1 element a cycle a leaf (5 a slice),
so a leaf's ~64 SW elements a layer take 64 cycles instead of ~5; +~60 cycles on each MoE layer's serial chain (~0.9% of
the MTP token if all 43 layers pay it). QB, RB, QR and MOE are at or above the SPEC rates.

## Bench (tools/s81_slice/vs_bench.sh; logs in bench/)

vp + vs + vsw + the RA pair + vq, driven only through vp's ports, on the su_cases of L0 and L2 (every golden asserted
against the hub executor's check). Base PASS on L0 and L2: SW 29 row pairs, RA 1, RB 48, QR 8, MOE 8, and 2 vq XQ beats
(SW -> quant2, QB z_quant), 0 mismatches, no fault. Negative controls, all FAIL as required: MUT 1 SW without w (209
words), 2 RB without bias (384), 3 QR inverse rotation (64), 4 MOE BF16 partials (22), 5 QB swapped halves (XQ beat), 6 RA
rows shifted (4). A reversed MOE expert order is NOT visible on these rows: the FP32 order differences vanish under the
final BF16 rounding, so the order control was replaced by the rounding-point control.

## KV and QN norms: proposal (not built)

Both are RMSNorms whose vectors are not the slice-aligned h vector:
- **QN** (q_lora norm): 1,536 elements spread over ~4.8 slices. The 32-element dealing does not align the slices'
  ranges to golden csum subtrees, so a leaf's partial is not one aligned subtree.
- **KV** (kv row norm): 512 elements (one head) in 1-2 slices, then RoPE on its tail and FP8 QDQ.

vn's pattern (beat partial = aligned subtree -> xr collector -> xfin exchange + replicated finish -> rstd back) reuses
cleanly only if every contributing leaf's range is a union of aligned golden subtrees. What is needed:
1. **Placement rule (compiler):** deal QN / KV rows to leaves in aligned 64-element groups (QN: 24 groups over 24 leaves
   of 4.8 slices; KV: 8 groups). Then each leaf's partial is one aligned 64-leaf subtree, as for h.
2. **vs ops:** NP (x^2, golden chunk-of-8 chains, the 3-level beat tree: vn's `ot_hbm_norm_grp` front without the hc_pre
   mix) -> partial out; NS (y = BF16(w (x r)), plus KV's rope_tail via the QR lanes and FP8 QDQ in vq) once the rstd
   arrives.
3. **Partial exchange path:** vs needs a partial output and an rstd input on the centre leaf's xr collector (as vn's
   p_v / p_d, rb_v / rb_d), and the xfin needs a per-vector configuration of which slices contribute and the golden
   tree shape above the 24 (QN) or 8 (KV) subtree roots (not a power of two for QN: the golden pads the chunk-sum tree
   with +0, so the finish must insert the zero leaves at the same positions).
4. Cost: NP adds about one norm group (~6-8k flops) to every leaf, so it is probably a third sub-leaf (vs_n).

Recommendation: decide 1 and 3 at the xfin / compiler level first; vs then adds NP / NS on a vs_n sub-leaf.
