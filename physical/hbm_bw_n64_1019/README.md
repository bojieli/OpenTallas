# hdie_pc_ctrl_bw_n64: SAFE n64 HBM PC controller (LH-BW, 10-19)

Top `ot_hbm_svc_pc_ctrl_leaf_cfg_safe_legacy`, branch `claude/lh-bw-n64-1019` (base RTL cc723735d plus the n64 store change).
Spec `tools/ref_tile/specs_hbm_bw_safe_1019/hdie_pc_ctrl_bw_n64.json`, kit `physical/ref_tile/hdie_pc_ctrl_bw_n64`.

## Why a structural redesign
The safe3/safe4/composed gates failed, and the map4-map6 censuses failed too. The cause is structural: the 13 `ot_sram_1r1w_128x256_m1_r2c2` macros put
410/409 signal pins on 41.064 um W/E faces, which is 10 pins/um. Most of those pins were tied: metadata words are 79 bits, identities 21 bits and the AQ queue 30 bits,
so 177, 235 and 226 bits of padding were tied in every word, and every 256-bit write mask was tied as well. The n64 change stores every word in ceil(W/64) x `ot_sram_1r1w2c_128x64_m1`
macros (`ot_hbm_svc_sram128_n64`). Each of those macros has 105 pins on each 27.576 um face, which is 3.8 pins/um. The change uses 23 macros with 21.4k um2 of macro area instead of 50.6k. Synthesis drops the upper 64-bit half of each head replica because its 15 bits are never read, so 27 instantiated macros become 23 real ones.
The read edge and the write behaviour are unchanged, so it adds no cycles.

## Floorplan
- Outline: 561.6 x 367.2 um (1.53:1), 206.2k um2. The composed outline was 205.3k um2.
- Macros: 6 columns x 4 rows (23 used), with origins on the 43.2 lattice at 86.4 um pitch. That leaves 52.7 um vertical pin channels and 58.8 um row gaps.
  - A 43.2 row pitch (15.6 um gap) fails the >=20 um channel rule.
  - Abutted stacks put the pins off the M2/M4 tracks, because 27.576 is not a multiple of 0.576.
- Std-cell area: one full-width central band at y157.2..216, connected to every channel. There is no fence and no island.
- Clock: enters on the W face, M4, at y186.624, the centre of the band.

## SAFE-DESIGN checklist (owner 10-19)
1. **Pins: PASS (inherited).** The RTL registers the pins natively (OREG/KREG/KRREG/RREG=1, H9b K capture, KR registered readiness).
   Reset lands in 2 kept face stages in RTL, followed by a native 3-edge relay (5 release edges). The tool's duplicate landing is disabled, with the reason recorded in the spec.
2. **Reach: OPEN, measured at the gate.** The tile is 561.6 x 367.2. A 256-bit bus bit whose face pin lands far from its 64-bit macro can exceed 405 um. The gate's reach audit decides.
   If it fails, the next step is to order the bus pins and macro slots per 64-bit slice, not to squeeze.
3. **Fanout: OPEN.** map6 (RTL 0b823) still has 5 nonreset roots of 33-42 loads and 43 static reset roots.
   cc723735d adds head_bank_cfg captures and regional bank muxes for those roots. This gate's synthesis is the map7 census.
4. **Depth: measured at the gate.** The previous synthesis depth was 528.4 ps. n64 changes only the macro boundary.
5. **Storage: PASS.** Every runtime-indexed store over 2 kb is SRAM, and no word is padded with tied macro pins.
6. **Floorplan: PASS by construction, except low fill.** Macros sit on the 43.2 lattice, faces are 3.8 pins/um, channels are 52.7 um, halo is 5.4 um, aspect is 1.53, and there is one connected std-cell region.
   Utilisation is about 3% (std area about 6.5k um2), so the outline is set by the macro channels, not by fill. Low fill was already accepted for the composed outline (coordinator 10-19).
7. **Clock: OPEN.** The W-face mid-band spine spans 561.6 um, under the 600 um WARN. The binding check is pin-flop spread <=80 ps at TT and FF, measured at CTS.
   io_hold_margin is 0.03 (PASS). The 1024 ps single_clock_contract (main tools) is not yet bound, so sign-off stays at 833 ps. That is conservative and not a waiver.
8. **Schedule: PASS.** The schedule is static and n64 adds 0 cycles. The BW cadence cost (G320/96 warm-up, 90.67 B/edge) is priced in `results/.../hbm_bw_safe_1019/pricing_lhbw.json`.

## Proof chain owed before submit
- AQ64 regions8/banks8 positive, plus HEAD/ACT/REFRESH/WRROW/BANKREG mutants.
- 6000-transaction data exactness, plus the identity mutant.
- Controller rate for DS seeds and packed.
- Production 66-op / 154-GO full96 run (G320/PADD8/FETCH96, HBM_SAFE_COMPOSED).

The runs are recorded in pending_results (LEAD-HBM/LH-BW).
