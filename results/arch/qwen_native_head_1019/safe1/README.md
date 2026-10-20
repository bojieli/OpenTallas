# Q.SAFE.HEAD safe1 -- structurally safe native ML5 head (QW-CLUSTER3/HEAD, 10-19)

Source: `rtl/qwen_dv/qfd_dv_head_safe1.sv` (top `qfd_dv_lane_h_safe1`), a new file; the predecessor
`rtl/qwen_dv/qfd_dv_head_native_b64.sv` (@5cd31ebb8, CONTROL_SAFE=1, terminal PASS cd660e13e) is untouched.
Bench fixture `rtl/test/qwen_dv/qfd_dv_su_lane_safe1_fixture.sv` (copy of the native fixture, head module renamed),
runner `tools/qwen_native_head_1019/run_safe1_production.py` / `run_safe1_bench.sh` (Verilator 5.050, fleet).
Kits: `physical/ref_tile/qfd_dv_lane_h_safe1` (302.4 x 172.8) and parallel fallback `qfd_dv_lane_h_safe1w`
(345.6 x 172.8, lower density / more routing room). Same RTL, same macro stacks.

## Structural changes (values and every port cycle = the CONTROL_SAFE=1 head)
- Reset: `rst_n` -> `qfd_dv_s1_rst_land` (2 registered stages, async assert / sync release; rst_n's only sink) ->
  3 `qfd_dv_s1_rst_relay` branches -> 11 leaf relays (all at depth 4). Leaf loads (RTL count): face 15, ctl 15,
  guards 18, ml rings 20, d38/d914 20, tap0+TLS ptrs 24, dmc/dmd/daddr 25, FPU pairs ~10-14 each, SFU ports 7.
  The old single `rt` drove 1,603 sinks. FPU payload reset off (`DRST 0`, valid bits only; results valid-tagged).
- Kept same-edge copies (unparameterised `qfd_dv_s1_cp1/cp4/cp5`, `keep_hierarchy` on the definition, so the
  attribute survives paramod renaming and opt_merge cannot fold them): ring_on x5 (was 130 loads: 4 x <=32-bit tap
  groups + macro CEs) and the class one-hot (s_val select) registered at the face from the `cls` pin on the same
  edge as `q_cls`; S1 lane select x4 (was 128 / 64: one copy per 4-bit weight group, one-hot AND-OR mux, no runtime
  part-select); bsrc x3 (was 65); mc flag duplicated in the dmc ring's spare column 127 (was 33).
- Holding chains: imm1/ma/mb/ad/imm2 + 62-bit tail (the 97 depth-4 and 36 depth-3 SRAM-capture/tag chains) ride a
  separate native ring of age ML+2 (q = the S2 value) and land in one flop (s3) before the next ring; daddr (24
  depth-3 SRAM->output chains) rides its own ring of age LM+1 whose capture flop is the lane write-address register.
  Macros: 15 x ot_sram_1r1w_32x64_m1 (+2 vs 13) + 2 x ot_sram_1r1w2c_128x64_m1 (TLS, unchanged).

## Priced cycles (die schedule)
- Steady state: **0** added cycles on every path (copies are same-edge, rings keep their ages).
- Reset release: +3 edges after rst_n deasserts (landing 2 + branch + leaf = 4 vs old rt 1); boot only, absorbed by
  the existing RESET_WARM 18 guard in the production bench (scalar16 + landed SU2); report to the die reset ledger.
- Area: +2 native 32x64 macros (~1,105 um2), +12 kept copy FF, +16 reset relay FF; -2 x 133 tag/tail FF and -24 daddr FF.

## Safe-design checklist
1 Pins: PASS -- every input lands in one face flop, every output leaves a flop; reset lands in 2 stages (rst_land).
2 Reach: gate-measured (tile <= 345.6 um wide; no single-cycle face-to-face path: every port is registered).
3 Fanout: fixed for reset (1603 -> leaves <= 32), ring_on 130, lane 128/64, bsrc 65, mc 33. WAIVED: shared FPU
  library internals (ot_hdc_fp32_mul_lat / add_lat: s2_sh 48/40 shifter amount, top 43, c3 34, b2_in 36, c2_in 33,
  exponent-compare cones 89-119) -- unchanged closed-library units, single-stage local cones inside one FPU; a
  library successor (KCP-style copies) is the follow-up, not a head change. Combinational n_out (43) and the
  class compare cones (33) are gates, not register roots.
4 Depth: gate-measured; no combinational in->out (both faces registered); wide muxes use registered selects.
5 Storage: PASS -- every delay >= 3 deep is a native SRAM ring; remaining flop chains: 20 pin-address D3 (face in ->
  lane address stage -> face out, W face to S face, waived: both face regs mandatory, the middle is the lane's
  address stage) and the 24 mixed reset/arith chains the hold model preserves.
6 Floorplan: macros at x in {43.2, 129.6, 216} (43.2 lattice), abutted N-S stacks from y 43.2 (TLS at 43.2 / 70.8 as
  the closed q3 kit), >= 54 um E-W channels, >= 20 um from every pin face, E face pin-free; one full-width std band
  above and below the stacks; util / synth area: see gate_result.json (outline 302.4 x 172.8 assumes ~11k um2 std).
7 Clock: single CTS root from the N-face clk; gate measures pin-flop spread TT/FF <= 80; io_hold_margin 0.03.
8 Schedule: static, no credits/backpressure; 0 steady-state cycles added; +3 reset-release edges priced above.

## Mutants (numeric e must FAIL; fail witnesses in witness/)
TLS bank swap (OT_HEAD_B64_BANK_MUT), TLS slot (OT_TLS_MUT), new copy mutant OT_HS1_RON_MUT (ring_on copy 1 = 0).

## Results (10-19)
- safe1 (SRAM rings) @f1de19bf5: benches m0 PASS (e 1024/1024, a24 c640 f3 g5 k512 q512 m8 o2 n2; g ages 189/140/110/70/196
  unchanged), mutants bank FAIL 0/1024, slot FAIL 1/1024, ron FAIL 10/1024 (witness/). Gate qfd_dv_lane_h_safe1 FAIL fill 29%:
  synth std 5,083 um2 vs 10,146 um2 of macros whose 20 um channels dominate (spread TT/FF 31.6/31.7, GRT ovf 0). Kept copies
  survived synthesis (10 cp1, 4 cp4, 1 cp5, 14 relays, 1 land); reset_landing rst_n 2 sinks. safe1 is history.
- safe2 (= safe1 RTL with FLOP 1: every fixed-age ring < 2 kb as a flop ring of 16-bit slices, own pointers + leaf relays
  on branch r_br[3]; only the 2 TLS natives) @76cd5e0d5: benches m0 PASS identical (e 1024/1024 + W10, same ages), mutants
  bank/slot/ron FAIL 0/1/10 of 1024 (witness_safe2/). Gate qfd_dv_lane_h_safe2 151.2x129.6 WARN 0 fail: std 8,305 um2,
  density 55%, 10,918 flops one root, TT/FF pin-flop spread 62.0/59.1 ps, TT insertion 300.7, GRT overflow 0 (M2 40%),
  reg->reg worst +13.2 ps, hold WNS > 0, depth WARN 620 ps (md_x -> u_md s1_rows, library mul stage 1). Fallback
  qfd_dv_lane_h_safe2w 172.8x129.6 WARN: density 47%, spread 64.1/60.1, ovf 0. PNG reviewed: TLS stack at x 43.2 on the
  lattice, one full-width band around it, even density, no hot spots at pin faces.
- safe2 checklist deltas vs above: 5 Storage PASS (rings are flop ring buffers, no flop->flop hold chain: write enable in,
  read mux out; each ring < 2 kb); 6 Floorplan PASS (util 55% / 47% from synth area, 1 macro stack); macros 2.
