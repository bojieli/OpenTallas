# KV-AHUB3 (10-19): the attention hub as a landed-region cluster

Lane KV-AHUB3 (LEAD2-KV, tree K.STA.AHUB). Input: KV-AHUB2 `7222d4264` (results/arch/kv_ahub2_1019, README section 5 steps a-d).
Branch `claude/kv-ahub3-1019`.

## Why
Both single-root SAFE hub kits (`qkd_ahub_sfa` / `qkd_ahub_sfb`, source `qkd_ahub_static_dw_safe`) failed the clock rule
terminally: pin-flop spread 86.5 / 97.3 ps and 116.3 / 123.2 ps (TT / FF). One insertion-aware spine over 734.4 x 540 um pads
every hub flop to the hard children's insertion (ot_nhb_zh 246.5 ps, ot_qkh_recip_leaf 238.7 ps). Structural redesign
(not a squeeze): local region roots with landed crossings (landed-regions standard 10-18).

## What was built
| step | result |
|---|---|
| a. two-clock landing | The core <-> Z-tree buses cross through the standard `ot_pl_land_chunk` landing (lp.py): the write ring and write pointer sit on the source root, the free-running read pointer and the flop-last read on the destination root. Epochs come from equal-depth regional reset runs. D 4, E = K 2, +3 edges, fixed latency, no ready / credit. Chunks are 8 b with kept per-chunk selectors, and a per-chunk reset forest keeps leaves at 32 or fewer. This **replaces** the private grouped ZH transport (KV-AHUB2), which had one `phase` for both write and read and was common-clock only. That transport stays component evidence and is not used. |
| b. hub RTL with regional clocks | `rtl/hdc/nearhbm/qkd_ahub_static_dw_g2.sv` is a wires-only flat form of `qkd_ahub_static_dw_safe`: same children, nets and relays, ap / zh_err flops as `ot_qkd_drly` children, no internal reset synchroniser. `tools/landed_parent/specs/qkd_ahub_static_dw_g2.json` feeds `lp.py gen`, which writes `rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g2_lp.sv` (+ .sdc, lockstep tb, bench) and the record `qkd_ahub_static_dw_g2_lp_record.json`. Regions: `c` (io / core / pin flops / RS-RX-RY-WF relays / reciprocal leaf) and `z0..z3` (one Z tree each). Totals: 8 landings (4 x 268 b c->z, 4 x 68 b z->c), 0 pads, reset depth 3, audit PASS. Added flops: 10,332 landing + 413 reset. The core<->tree loop is a cross-region LOOP, so the generator uses schedule `reference`: the landed parent equals the flat parent with `ZW_RLY = ZR_RLY = 3`. |
| c. calendar | The Z round trip is +6 edges (2 landings x 3). The compiler moves **HUB_RECIP +6 and HUB_PUB +6** (RECIP / PUB law recip+75 unchanged). PV_START, R, EXP, the hub input ages and the fr export edge are unchanged. The core's calendar check becomes `RECIP > Z_START + 77 + Z_RT` (new parameter `Z_RT` in `qkd_ahub_static_core_la_safe`, default 0 = unchanged; g2 passes `ZW_RLY + ZR_RLY + Z_LAND`, and the landed build has `Z_LAND 6`). |
| d. kits | `physical/ref_tile/qkd_ahub_g2l` (MAIN): multiple_cts_roots ck_c + ck_z0..3, landed_record, RTL synthesis with OT_KEEP_REGS + keep_pin_regs + pin_reg_split. The kit splits the 4 am copies per bit per face, which is the 105 face copies of 4b05445f7 done at source level instead of from the fixed-hash native netlist. `physical/ref_tile/qkd_ahub_g2c` (FALLBACK, PARALLEL rule): the same flat hub on ONE a7 spine with the landings' latency as 3 registered relay stages each way (landed=false). Both kits keep the reviewed a7 / sfa geometry. |

## Evidence (fleet ot-epyc6, Verilator 5.050; logs in results/rtl/qwen_kv_ahub3_1019)
- **Die-calendar bench** `tools/qwen_kv_die/ahub3/g2_bench.sh` (tb `rtl/test/qwen_kv_die/tb_qkd_ahub_static_dw_g2.sv` = the HKV-AHUB5 / KV-AHUB7 die bench with the landed DUT; the reference sealed hub runs ZW/ZR 3; all 7 HKV-DIE3 calendars with HUB_RECIP / HUB_PUB +6).
  - **m0 PASS**: 7 passes, 680 Z words, fr exactly once per pass on pvfin's R slot, 32 beats each, am 28, FR_OFS -7, AP_OFS ffd9ffdaffd8ffd8.
  - Mutants 1-13 and 15 FAIL. **m13** (calendar NOT shifted) FAILS with 13,640 errors, so the +6 is required. **m15** (landing 0 read one edge late) FAILS with 19 errors.
  - m14 (landing 0 bypassed, 3 edges EARLY) and m16 (core reset run one stage long) PASS at the die-bench level. Both are benign there: an early Z command and a late core reset are absorbed by the calendar's slack. Both are caught cycle-exact by the lp lockstep bench (lp MUT 1 / 4), and they are not used as kit fail benches.
- **lp.py lockstep** (`rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g2_lp_bench.sh`, Verilator 5.050): the landed parent vs the flat reference (ZW/ZR 3), cycle-exact on every output and on every u_zh* / u_recip pin. 9000 cycles; passes every 2000 edges on a T 1000 calendar, plus starts on every edge until the reference core's regional reset releases.
  - **MUT 0 PASS** (448,205 compares).
  - MUT 1 (landing bypass) FAIL, 23 mismatches. MUT 2 (K+1) FAIL, 18. MUT 4 (u_core reset run +1) FAIL, 23,408.
  - BENCH_EXIT 0. The region audit PASSES and the unland mutant FAILS it.
  - Logs: lp_bench.log, lp_mut*.log, lp_audit*.log.
- **Fallback flat bench** (FLAT=1: `qkd_ahub_static_dw_g2` with ZW_RLY = ZR_RLY = 3 and a 2-stage reset landing): **m0 PASS** on the same 7 calendars with HUB_RECIP / HUB_PUB +6.
  - FAIL: m1 / 11 / 12 / 13. m14 (ZR_RLY 4, root one edge late) FAILS with 19 errors.
  - ZR_RLY 2 (one edge early) passes: early is benign, as with the landed m14.
  - Logs: flat_m*.log.

## Safe-design checklist (design review before the gate; PNG items filled after the gate)
1. Pins: **PASS**. Every input lands in a flop (u_io pin flops, u_apq) and every output leaves a flop (core am regs, u_rw, u_io fault). Reset: port -> u_lpr_root -> region forest -> child pads, at least 2 registered stages.
2. Reach: **PASS by construction**. The ~650 um core <-> tree legs are now landed: ring -> read is multicycle E 2 / hold D-1 3. The a7 relays (RS / RX / RY / WF) stay on the other > 405 um legs. Reset hops are planned at 405 um (RB 3). The gate's wire-per-stage lint verifies.
3. Fanout: **PASS by construction**. Landings use 8-b chunks with kept selectors and reset-forest leaves of 32 or fewer. The core uses SAFE1 one-hot selects. The gate census verifies, and synthesis keeps the copies with OT_KEEP_REGS.
4. Depth: **PASS**. The core is the a7 / SAFE1 core; the landing read is a 4:1 AND-OR per 8-b chunk.
5. Storage: **waived with reason**. The landing rings are 4 slots x 8 b per chunk (32 b each), written every edge. That is the standard LANDING-CONTRACT primitive, not a runtime-indexed store.
6. Floorplan: same reviewed a7 / sfa geometry; zh0 / zh1 MX at y 43.224 keep the a7 lattice waiver (the closed view's clk / rst_n M4 pins are off-track under MX); aspect 1.36; full-width band. Util is measured at the gate.
7. Clock: regional roots ck_c / ck_z0..3 with landed crossings; io_hold_margin 0.03. Spread is measured at the gate.
8. Schedule: **static**. HUB_RECIP / HUB_PUB +6 and reset release +10 are handed to KV-GEN9 (lanes/KV-GEN9.md). Token cost is 0 edges (the fr edge is unchanged on all 7 calendars).

## Die obligations
- The die must deliver five related same-frequency hub clock entries (ck_c N 358-360, ck_z2 / ck_z3 N 118 / 334, ck_z0 / ck_z1 S 118 / 334), each within the L5 window of its neighbour.
- The compiler adds +6 to HUB_RECIP and HUB_PUB.
- Reset release is +10 edges.
