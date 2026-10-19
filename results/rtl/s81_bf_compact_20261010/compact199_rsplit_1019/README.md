# ot_v41_bf_col (compact199) FALLBACK kit `s81sf_bfcol_c199r` (S81-SAFE-FIX/C199, 2026-10-19)

**State:** this is the ready successor if route `bfh_compact199_col_pinreg_prepabs_1019` misses. That route is not touched by this work.
- The tile is critical (`ot_v41_bf_`) and has 3 failed routes since its last CLOSED, so it goes to coordinator review. It is never submitted by the lane.
- Kit: `physical/ref_tile/s81sf_bfcol_c199r/` (spec `tools/ref_tile/specs/s81sf_bfcol_c199r.json`), branch `claude/s81sf-c199-fallback-1019`.

## What changed vs the closed / running compact199

1. **Depth (item 4): RSPLIT.** This is a zero-cycle retime of the deepest stage.
   - The stage is the BF lane multiplier's subnormal RNE encode in `ot_v41_bmul2_rne_prepare` (XS = 1): `g_l[6].u_m.s3_be -> g_x4.r_gy`, textbook estimate 626.8 ps over 15 levels.
   - Opt-in define `OT_BMUL_RSPLIT`; default off leaves the circuit unchanged in function.
   - Stage 3 also registers the shift amount `1 - s3_be` and its range, computed in parallel with the bias add.
   - Stage 4a registers `{retained, increment, zero}` instead of the 32-bit encoded result.
   - The 24-bit increment and zero select move in front of the existing stage-4 result select.
   - Exact by construction: `rounded == 0 <=> retained == 0 && !increment`, because `retained = sig24 >> shift` with shift >= 1 is below 2^23.
1b. **Fanout (item 3): TAGREP** (opt-in define `OT_BF_TAGREP`, `ot_v41_bf16_lanes3`).
   - The first gate's lint (@69048c352) found the BF tag line `u_pt line[..]` driving 4,272 loads.
   - Its last stage is now a kept per-lane register on the lane's own gated clock (same enable function), so each copy drives about 270 loads.
   - Same delay PL, same edges: 0 cycles.
2. **Flow:** the bespoke `route_hier.sh` recipe is replaced by the mandatory ref_tile kit. It sets reset landing, io_hold 0.03, the lattice, pin faces and util by construction.
3. **Floorplan (item 6):**
   - Outline 432.0 x 216.0 (2:1). It was 450.144 x 198.72 (2.27).
   - Placement density is about 0.556, using gate2's std area of about 39.2k um² (before hold repair) over the placeable core.
   - Both ROMs sit on the 43.2 lattice at x 43.2: u_rom0 R0 at y 129.6 and u_rom1 MX at y 43.2.
   - Their pin faces share one 23.45 um channel: 2 x 288 pins over 125 um, 2.3 pins/um.
   - The 777 inputs spread over the FULL E face (3.6 pins/um). Before, they sat on a 74.5 um span at 10.4 pins/um.
   - The 64 outputs are on the S face. clk is on the N face at x 298-302, above the register mass.
4. **Reset (item 1):** `reset_landing {"enable": true, "stages": 2}` on `rst_n_pin`.

## Bench and exactness (Verilator 5.050, fleet ot-agidock128, source 1b038f73a)

| case | result | witness |
|---|---|---|
| rsplit (positive, `+define+OT_BMUL_RSPLIT+OT_BF_TAGREP`) | TXN MATCH, compared=456; lag 5.831/14.994/9.090 ns n=456, **identical to the closed full.json** (0 cycles) | bench_5050/positive_run.log |
| rs_mutant_{dp,recut,pinlat,tcg,xst,fxst,tagrep} (each with RSPLIT+TAGREP; tagrep = lane 5's `first` copy inverted) | 7/7 `%Fatal ... DIFF TXN lane=` | bench_5050/fail_witness/*.log |
| formal miter vs closed `ot_v41_bmul2_rne_prepare` (24cf7e2e3), GRADUAL_RNE=1 XS=1, BMC 20 steps, outputs from step 10 | `SAT proof finished - no model found: SUCCESS` | equiv/equiv_mut0.log |
| formal miter with RSPLIT_MUTANT_INC (round-up inverted) | `model found: FAIL` (counterexample) | equiv/equiv_mut1.log |

The formal check is the exactness proof for the moved logic. The TXN bench vectors may not hit subnormal products, so the formal miter, not the bench, covers that logic.

## SAFE-DESIGN CHECKLIST (owner 10-19)

| # | item | result |
|---|---|---|
| 1 | Pins / reset | **PASS + fixed.** Every input is registered at the face in RTL (`g_pin.r_*` kregs, incl. ze_d and the reset synchroniser), and every output comes from a register (gate2: 839/840 register-at-pin; a_ctr[13] is unused). Kit `pin_regs` is opted out with that reason, so no second layer and 0 edges. io_flop_at_pins anchors the RTL pin flops. Reset now lands in 2 stages (kit). |
| 2 | Reach <= 405 um | **PASS.** The textbook lint reach is 0.0 um (running route). The longest face is 432 um, and every pin goes to a face register. |
| 3 | Fanout | **fixed** (TAGREP: tag line 4,272 -> about 270 loads per copy). Residual lint WARNs are the tile reset synchroniser outputs (u_tt.u_rs 552 and g_mz.u_rst 285 async-reset loads > 256): an async assert with release timed by recovery/removal STA, not a datapath cone; repair_design buffers them. Waived for this kit; a regional ot_rst_relay is the next step if the gate's recovery check shows them. |
| 4 | Depth <= ~600 ps | **fixed.** The 626.8 ps stage is retimed (RSPLIT, 0 cycles). The gate lint @69048c352 gives a maximum of **493.4 ps / 13 levels** (u_c.u_add c6 -> c8). |
| 5 | Storage | **PASS.** Weights are in 2 ROM macros. BXST/FXST input stages are 2 deep (< 3), so there are no long flop delay lines. |
| 6 | Floorplan | **fixed.** 43.2 lattice, 2:1 aspect, density 0.556, full-face pins at <= 6 pins/um, one contiguous std-cell band (ROMs at the W edge, cells over the rest). |
| 7 | Clock | **PASS / waived-with-reason (regional landed roots).** The clock is centre-fed: N pin above the register mass, one TritonCTS tree with the per-lane TCG gate tiles as sub-roots. The rule check is pin-flop spread <= 80 TT+FF; gate2 measured 48.5/48.6 on this RTL. Regional roots with LANDED crossings are waived: the tile is 0.43 mm, below the ~1 mm parent/die-link threshold of the landed-regions standard. Its only hard children are the 2 ROMs (raw macro clock entries). Landing the ROM->lane and lane->tree crossings inside the tile would add >= 3 cycles on about 1k internal bits and about 4k ring flops with no clock-rule benefit. If the routed view of the running route or of this kit shows spread > 80, the split becomes mandatory and is the next successor. io_hold_margin is 0.03. |
| 8 | Schedule | **PASS.** Static schedule, no credits. Added cycles: data 0 (TXN lag identical); reset assertion/release +2 cycles (landing; a scheduled constant) -> MU-DIE-S81 INBOX. |

## Gate
`python3 tools/closure_loop/submit_exact.py physical/ref_tile/s81sf_bfcol_c199r/job.json --follow-head --regate --dry-run --gate-args "--remote auto --cts --mem 64"` (diagnostic; result paths in pending_results / lanes/S81-SAFE-FIX-C199.md).

## Open dependencies
- Slot change 450.144 x 198.72 -> 432 x 216 (frame col_h9 / col_h10 + MU-DIE-S81): +17.28 um per row and -18.144 um width.
- The E-face pins now spread over the full face, so the front tile's facing c0/c1 pins must be re-assigned top-down.
