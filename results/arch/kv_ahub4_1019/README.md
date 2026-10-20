# KV-AHUB4 (10-19): the attention hub with its face IO in its own clock regions (g3)

Lane KV-AHUB4 (LEAD2-KV, tree K.STA.AHUB). Input: KV-AHUB3 `500985c55` (both g2 kits failed the clock rule).
Branch `claude/kv-ahub4-g2-1019`. The name `claude/kv-ahub4-1019` was already taken by HKV-AHUB4's qkd_ahub_sdw work.

## Why g2 failed
- In qkd_ahub_g2l (gate l1), the core root ck_c owned four things at once: the core, the reciprocal leaf, the W-face pin flops (x 0) and the E-face pin flops (x 734).
  - That is 11,690 flops over 730 x 536 um.
  - TT soft flops arrived at 686.8..1029.7 ps vs u_recip at 655.6..674.3 ps. The spread was 374.1 TT / 331.4 FF.
- Without placement regions, the c->z write rings sat at the four Z sites, and u_core spanned x 9.6..730.9 (Codex census a1d3da487).
- The z->c write rings sat beside their core-side readers, so the Z roots spread 109..186 ps.
- The hard-child taps were NOT the problem. TritonCTS already taps each hard child early by about its insertion:
  - u_recip pin at 432.6 ps vs soft mean 703.4 ps (insertion ref 238.7);
  - u_zh pins at about 90 ps vs soft mean about 360 ps (insertion ref 246.5).

## What changed (structural, two variants submitted in parallel)
1. **RTL `qkd_ahub_static_dw_g3`** = g2 with the face IO split out. The landed form, `lp.py` -> `rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g3_lp.sv`, has 7 regions:
   - **c**: io (hs pins, hf), core, relays, reciprocal leaf;
   - **w**: ap0/ap1 pin flops u_apw, am0/am1 face drivers u_amw, fr export relay u_rw;
   - **e**: ap2/ap3 pin flops u_ape, am2/am3 face drivers u_ame;
   - **z0..z3**: one Z tree each.

   There are 15 landings (D 4, E = K 2, +3 edges each, no ready / credit). Reset depth is 3. Flops added: +13,876 for landings and +538 for reset.

   New latency parameters:
   - AP_RLY / AP_LAND: the core's input ages are AP_OFS + 3. **AP_OFS keeps its die meaning.**
   - AM_RLY: am leaves through the c->face landing.
   - FR_RLY / FR_LAND: u_io leads by WF_RLY + 3, so **fr stays on pvfin's R slot and FR_OFS is unchanged**.

   With every new parameter at 0, g3 is edge-exact with g2.
2. **Placement fences** (`lp_fences.tcl`, from `tools/qwen_kv_die/ahub4/mk_kits.py`): one INCLUSIVE region per clock region. The landing halves sit beside their source or their reader. Port-net cells (pin flops, pin hold stages) are left to io_flop_at_pins.
3. **Kits**
   - `qkd_ahub_g3a` (A): the reviewed a7 / g2l geometry. The core fence is the logic band between the Z input strips, plus the strip under the reciprocal leaf.
   - `qkd_ahub_g3b` (B): re-floorplanned. Z trees sit at the four corners and the reciprocal leaf at bottom-centre with its x inputs facing up. The core fence is at the block centre, directly above the leaf.
   - B moves the ck_z1 / ck_z3 entries to x 594-596.

## Die / compiler deltas (handed to lanes/KV-GEN9.md)
- HUB_RECIP / HUB_PUB: +6, the same as g2. No further shift: bench m0 PASSES with CSH 0, and CSH 3 also passes.
- **am reaches the ASTK pins +3 edges later than g2** (am lag D_HS+1 -> D_HS+4). The ASTK am consumer must take +3. Mutant m19 (die keeps g2's am edge) FAILS.
- AP_OFS, FR_OFS and the fr edge are unchanged.
- Reset release is +10 edges, once per reset (lp record).
- Clock entries, all related at the same frequency, each within the L5 window of its neighbour:
  - ck_c N 358-360, ck_w W 350-352, ck_e E 304-306;
  - ck_z0 S 118, ck_z2 N 118;
  - ck_z1 S 334 and ck_z3 N 334 (A), or S 594 and N 594 (B).

## Evidence (fleet, Verilator 5.050; logs in results/rtl/qwen_kv_ahub4_1019)
- **Die-calendar bench** `tools/qwen_kv_die/ahub4/g3_bench.sh` (tb `rtl/test/qwen_kv_die/tb_qkd_ahub_static_dw_g3.sv`) on all 7 HKV-DIE3 calendars: see `summary.txt`.
- **lp lockstep bench** (`rtl/hdc/nearhbm/lp/qkd_ahub_static_dw_g3_lp_bench.sh`): the landed g3 vs the flat g3 with ZW/ZR/AP/AM/FR_RLY 3, plus MUT 1/2/4 and the region audits.
- Gate results and PNG reviews: in each kit's README.
