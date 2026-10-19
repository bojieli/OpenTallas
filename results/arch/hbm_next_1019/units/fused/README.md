# FUSED HC_PRE_NORM / HC_POST N-row engine (HBM-NEXT-UNITS-FUSED, 2026-10-19)

**Verdict: PASS.** The engine is bit-exact for N = 1, 2, 3, 4 and 6, for both ops. All 6 mutants FAIL, and their fail witnesses are committed.

**Measured row II (Verilator 5.050, fleet):**

| Op | Measured II per added row | CMTP price (isa_rows.py) | Ratio |
|---|---|---|---|
| FUSED.HC_PRE_NORM | **81** | 197 (credited P6 LL engine) | 0.41x |
| FUSED.HC_POST | **103** | 100 (priced) | 1.03x |

This is next-release work at P = 4, not a release gate. Branch `claude/hbm-next-units-fused-1019`. It uses only hnx names and edits no d4g/GEN2 file.

## Why a new engine (not a fork)

The d4g GEN2 die has **no FUSED HC datapath**:

- layer_coverage maps HC_PRE_NORM / HC_POST onto the static HC masters, but those masters implement HC.HC_MIX only.
- The die contract lists the producer as open gaps G-HC / G-HC-ENG.

The P6 RTL that the price of 197 comes from (8fe5d18bd, `ot_hgi_hc_eng_ll`) is a credited engine (credits, ready, request/grant, FIFOs), so it is illegal on the static die.

`rtl/hbm_next/fused/ot_hnx_fused_eng.sv` keeps the LL engine's arithmetic exactly: the same primitives in the same golden order. It replaces the control with a static calendar:

- Every VM read is issued on a counter-fixed edge.
- Every response is checked against its fixed return edge (RR + 1).
- Any collision is a FAULT: x-slot reuse, heap node overwrite, sweep overlap, a scalar read inside the data calendar, or an unsolicited response.

There is no "N = 1 = d4g" reference, because d4g has no such unit. N = 1 is checked against the same golden as every N: `tools/hdc_golden_v41`, R-ARITH chunk8.

## Structure

- **`ot_hnx_fused_lane`, x32, one per VM bank.** Lane-local: it reads and writes only its own bank.
  - Per record: JOB (ROWX fields nm1, rgap, rs_A/rs_B/rs_O in sectors), scalar sector reads, per-row WGT beats into 2 row-tagged coefficient slots, then GO.
  - PRE: the gain is read once and held across rows. Each row then does 4 NM h-reads, the mix into x slot p mod KX, the squares, and the chunk chain. Row p's r scales its x slot, giving y = bf16(w * (x * r)).
  - POST: per sector, 5 reads, then a 4-row sweep.
- **`ot_hnx_fused_top`:** job decode, the scalar prologue, relayed command/r buses, the golden csum tree with lanes in lockstep, and a row-pipelined padded heap. A node is cleared on consume, and a write to a full node is a FAULT. Then / D, + eps, rsqrt.

## Measured cycles (KX = 4, rgap 0; `m0/verdict_m0.txt`, bundle f6d6de957, ot-epyc5)

| N | 1 | 2 | 3 | 4 | 6 | II per added row |
|---|---|---|---|---|---|---|
| HC_PRE_NORM | 404 | 486 | 567 | 648 | 810 | 81 (= 4 NM + 1, NM = 20 at D 5,120) |
| HC_POST | 196 | 304 | 407 | 510 | 716 | 103 (= 5 NM + 3) |

- **Cost model for CMTP:** c(N) = c1 + (N - 1)(II + rgap).
  - PRE: c1 = 404, II = 81.
  - POST: c1 = 196, II = 103. The N 1 -> 2 step is 108.

### KX = 2 (`k2/k2.log`), HC_PRE_NORM at N = 4

| rgap | Result | Cycles | II |
|---|---|---|---|
| 0 | **FAULT** | | |
| 64 | PASS | 840 | 145 |
| 128 | PASS | 1,032 | |
| 192 | PASS | 1,224 | |
| 256 | FAULT | | |

- rgap 0 FAULTs because the x-slot collision check fires, as intended: the slot is reused before its scale.
- rgap 256 is a bench artefact. rgap is 8 bits (HGI-1R `rgap` 15:8), so 256 wraps to 0. The vector generator should refuse values above 255.
- **Design point: KX = 4 at rgap 0.**

## Mutants (all FAIL; witnesses in `witness/m1..m6.log`)

| Mutant | Mechanism | Result |
|---|---|---|
| m1 | every row uses coefficient slot 0 | pre mism 10,183, post 40,878 |
| m2 | rs_A ignored | pre 15,343, post 61,337 |
| m3 | every row uses x slot 0 | 15,349 |
| m4 | heap not cleared on consume | fault=1, mism 15,816 |
| m5 | gain not held across rows | 20,480 |
| m6 | row 0's r for every row | 15,360 |

## Build note

32 flat lanes OOM at about 1.5 GB per lane. The bench is built with `--hierarchical` (`tools/hbm_next/hnx_fused.vlt` hier_block on the lane). That takes about 35 minutes and up to 60 GB on the fleet.

## Kit (new hardened tile)

`physical/ref_tile/hnx_fused_lane_1019` is the lane, replicated x32 and hardened once.

- Outline 259.2 x 259.2 um, which is a **guess**. The remote gate prints the synthesized area, and gen should then re-size the outline from `std_area_um2`.
- Faces: N = command/up/r; S = VM bank (rq/rr/wq).
- io_hold_margin 0.03; reset landing 2 stages; pin_regs off (every port is a pin flop in the RTL).
- Benches: m0 (`m0 SUMMARY pass=10 fail=0 noresult=0`) plus m1..m6 with committed witnesses.
- **Remote CTS gate 10-19 03:04 (ot-epyc7): FAIL `synth_smoke`.** ORFS yosys did not finish within 2,700 s; it looped in OPT_SHARE / OPT_DFF passes. Log: `gate1_synth_stall.log`. This is a structural finding, not a flow glitch.
- **Cause:** the lane keeps the KX x NM x 256 b x store `xb[slot*NM + m]` (80 x 256 = 20,480 b) and the 20 x 256 b gain buffer `gb[m]` as runtime-indexed flop arrays. Each is read through an 80:1 or 20:1 x 256-b mux and written at a runtime index. That is the yosys SHARE-stall class, and it would also give a poor tile even if synthesis finished.
- **Fix (next agent, RTL):**
  - Move `xb` into one 1R1W SRAM macro (`physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_*`, 80 of 128 rows). The access pattern is 1 write a cycle (mix) and 1 read a cycle (scale), which fits a 1R1W macro.
  - Keep `gb` in flops, but read it through a registered address (or use a second 1R1W 32x256 macro).
  - Absorb the macro read latency into the scale pipeline (`xo` / `wm_d` delay +L). This is a fixed retime, so the row II is unchanged.
  - Re-run m0 + m1..m6 (the witnesses must be re-made if the logs change), then re-gate `hnx_fused_lane_1019` with `macros` in the spec.

## SRAM stores + gate n2/n3 (HBM-NEXT-UNITS-FUSED-SRAM, 2026-10-19)

- **RTL (5e2b4ea95):** the x store `xb` (KX x NM = 80 x 256 b) and the gain store `gb` (NM = 20 x 256 b) are now 1R1W SRAM macros
  `ot_sram_1r1w_128x256_m1_r2c2` (`u_xb`, `u_gb`). The macro read is registered (data the edge after the address, read-before-write),
  which is exactly the old `xo <= xb[..]` / `wo <= gb[..]` registered read, so the calendar is unchanged edge for edge. MUT 5 (gain not
  held) is now a sticky zeroing of every gain read issued after the row-1 edge.
- **Benches (Verilator 5.050, ot-epyc8, bundle 5e2b4ea95; `sram/`):** m0 `SUMMARY pass=10 fail=0 noresult=0`, cycles identical to the
  flop version (PRE 404/486/567/648/810 -> II 81; POST 196/304/407/510/716 -> II 103). m1..m6 all FAIL with the same mismatch counts as
  before (m1 10,183 / 40,878, m2 15,343 / 61,337, m3 15,349, m4 fault + 15,816, m5 20,480, m6 15,360); witnesses refreshed in `witness/`.
- **Gate n2 (259.2 outline + 2 macros, ot-epyc7):** FAIL synth_smoke again, but synthesis DID finish, in 4,438 s (cap 2,700): SHARE
  1,476 s + ABC 1,385 s. The lane is **852,881 cells / 94,740 flops, ~104k um2 std area** (72.6k comb + ~31k seq est.), i.e. the 259.2
  outline (67k um2) was ~3x too small. The cause of the stall is the size of the 8 flat element columns (deep FP32 pipelines), not the x store.
- **n3 (1073b91b5):** the 8 element columns are one kept module `ot_hnx_fused_el` (no parameter override, `(* keep_hierarchy *)`,
  `route.synth_keep_modules`) so yosys/ABC map it once; `SYNTH_ARGS=-noshare` (production precedent: hbm norm, tools/hbm_norm_noshare.py);
  outline 475.2 x 475.2 (util ~0.47 + macros). Benches m0 + m1..m6 and the `--cts` gate are RUNNING (pending_results).
- **DIE impact:** a lane is ~0.23 mm2 outline, so 32 lanes = **~7.2 mm2**, not the 2.15 mm2 (259.2 guess) in f4c_t8.
- **Parent (`ot_hnx_fused_top`, 32 lanes):** not kitted. It needs the closed lane view, and its geometry is open: the lanes sit beside
  their VM banks across 4 quadrants (DIE), so a single hardened 32-lane cluster (~2 x 2 mm with region clocks) conflicts with that
  placement. Proposed: kit the top's own logic (job decode, scalar prologue, csum tree, heap, divc, rsqrt) as a hub tile, with the per-lane
  RL relays as die-level forwarded hops; DIE/PROG to decide.

## Files

- RTL: `rtl/hbm_next/fused/ot_hnx_fused_eng.sv`
- Bench: `rtl/hbm_next/fused/tb/tb_hnx_fused.sv`
- Vectors: `tools/hbm_next/hnx_fused_vec.py`
- Fleet script: `tools/hbm_next/hnx_fused_bench.sh` (stages lint / m0 / k2 / m1..m6, plus a SUMMARY line)
- Verilator config: `tools/hbm_next/hnx_fused.vlt`

## Next

1. Do the xb -> SRAM macro fix above, re-bench, then re-gate `hnx_fused_lane_1019` (`--remote auto --cts`). Take the outline from the gate's `std_area_um2` plus the macro, then submit_exact. This tile is not on the critical list.
2. Kit the top (`ot_hnx_fused_top`: csum tree, heap, divc, rsqrt) as a cluster parent with 32 lane children. The DIE lane has to place the 32 lanes beside their VM banks.
3. CMTP: flip FUSED.HC_PRE_NORM to 81 MEASURED (c1 404) and FUSED.HC_POST to 103 MEASURED (c1 196), with the KX = 4 rgap 0 rule. For KX = 2, the compiler needs rgap >= 64 (the minimum between 1 and 64 is not measured).
4. The ROWX decode from the HGI-1R record word into the lane JOB (nm1, rgap, rs_A/rs_B/rs_O in sectors = words / 8) sits in the top's job decode. Check it against `tools/hbm_next/isa_rows.py` when CMTP's binary emitter lands.

## n3 gate verdict and n4 structural redesign (LH-P3UNITS/FUSED, 2026-10-19 11:30)

**n3 gate (ot-epyc6 `ref_gate/hnx_fused_lane_1019-20261019-060819`): FAIL.** Synthesis finished (kept `ot_hnx_fused_el`:
12,885 um2 / 12,523 flops each; lane 118,651 um2, 897,521 cells, **113,400 flops**). textbook_lint **REFUSE**:
clock_domain (113,400 flops on one root > 110,000) and high_fanout (one reset relay flop -> 16,053 async-reset loads > 8,000);
WARN logic_depth 617 ps (kk -> hcpost m4 input). CTS then stalled > 14,400 s in hold repair (worst -35.6 ps on the 20 x 11
`u_rmeta` flop chain, 9,400+ hold buffers); placement worst setup -123.8 ps at `wq_s[10]`. The client died; the stale GRT
container was killed (no gate_result). Benches m0 10/10 + m1..m6 FAIL were PASS on 1073b91b5.

**n4 (4028eb45b): halve the datapath instead of squeezing it.**
- HC_PRE_NORM's mix `x = bf16(((h0 p0 + h1 p1) + h2 p2) + h3 p3)` is exactly the first three sums of HC_POST's chain
  `o = bf16((((r0 c0 + r1 c1) + r2 c2) + r3 c3) + y p)`, and the two ops never run together (one record at a time, op static per
  record). `ot_hnx_fused_el2` keeps ONE f12 product/sum chain per element: PRE taps `bf16(s3)` (the mix's RNE), HC_POST
  takes `bf16(s4)`. Same f12 multiplier/adder cores (only register cuts differ); the sum-2/3 operand order is swapped
  vs the mix (IEEE add commutes). The lane loads the PRE operands into `op[1..4]` and zeroes `op[0]` (the `y * p` lane, exact 0);
  coefficients are `post ? wsw : pre_q` (static per record). Removes 4 multipliers + 3 adders + the 6/12-deep operand
  delays from each of the 8 columns (est. el 12.9k -> ~8.6k um2; lane ~85k um2 std, ~80k flops).
- Every delay line >= 4 deep is `ot_hdc_delay_ring RING 1` (u_rmeta 20 x 11, chunk-chain u_sd 32 x 6..36, u_wm, el2 u_d2/u_d3/u_d4).
- `ot_rst_relay REGIONS 9`: one kept relay copy per element column + control.
- Timing: x leaves at ML + 3 AL + 1 = 26 (was 24) -> PRE c1 +2 edges; POST c1 unchanged; row II unchanged (PRE 81, POST 103).
  CMTP: FUSED.HC_PRE_NORM c1 404 -> 406 (+2/record), to be confirmed by m0.

### SAFE-DESIGN checklist (owner 10-19), lane n4 `hnx_fused_lane_1019` and fallback `hnx_fused_lane_t648_1019`

| # | Item | Result |
|---|---|---|
| 1 | Pins registered, 2-stage reset landing | PASS: every input/output is a pin flop in the RTL (pin_regs opt-out documented: RR+1 counted from them); reset_landing 2 stages + ot_rst_relay. |
| 2 | Reach <= 405 um/cycle | PASS by geometry: 345.6 x 518.4, every pin <= 260 um from the centred macros; t648 fallback <= 324 um. Gate measures reach. |
| 3 | Fanout <= ~32 / kept copies | FIXED: reset 16,053 loads -> 9 kept relay copies (~1.2k each, buffered); broadcast `post`/`kk`/`sws` selects are registered control (n3 WARN `kk` 1,284 loads -> gate re-measures; replicate per column if it stays > 600 ps). |
| 4 | Depth <= 600 ps / 20 levels | n3 617 ps (17 levels) on kk -> hcpost m4: n4 adds a 2:1 static `post` select on b/p; f12 l7/l6r have an input-side cut. WAIVED-pending-measurement: if the gate depth stays > 600 ps, register the coefficient selects (cb*_q one edge ahead, kk_next). |
| 5 | Storage > 2 kb in SRAM; delay lines as rings | PASS: x store 80 x 256 and gain 20 x 256 in 1R1W macros (n2); all >= 4-deep delays are rings (n4). |
| 6 | Floorplan | PASS (local gate): macros on the 43.2 lattice (129.6, 172.8 / 259.2), centred, 45 um channel, std on all sides (one band); outline from synthesis (n3 measured el + lane-local; n4 estimate) at ~0.5; aspect 1.5 (t648 1.9). |
| 7 | Clock | PASS-pending: ~80k flops on one centre-fed root (WARN guidance > 15k; t648 WARN clock_span); the --cts gate measures pin-flop spread <= 80 TT+FF. io_hold_margin 0.03. |
| 8 | Static schedule | PASS: no credits/backpressure; +2 PRE c1 edges handed to CMTP (cost model c(N) = c1 + (N-1)(II + rgap)). |
