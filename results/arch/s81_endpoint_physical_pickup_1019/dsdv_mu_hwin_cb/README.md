dsdv_mu_hwin_cb -- HWIN central-band gate kit (Claude S81-MUEP 10-19), successor of the
unsubmitted dsdv_mu_hwin_central (95037b23f) on source codex/mu-hwin-central-1019 @1e057b7bf
(NEV16, HEAD_STAGE/COMPACT_PTR/CHECK_STAGE/LIVE_COUNT/RAW_SELECT/LOCAL_BOOT=1). Geometry unchanged:
388.8x561.6 (aspect 1.44), 84 ot_sram_1r1w_64x16 macros on the 43.2 lattice, channels 22.41/24.84,
one full-width std band y248.4..291.6; measured std 7780.1 um2 (sizing 37290b741) = 46.8% band.

SAFE-DESIGN checklist (pre-gate; the gate packet re-checks 3/6/7 on actual placement):
 1 Pins: PASS -- pin regs on (OT_KEEP_PIN_REGS), reset_landing 2 stages (rst_n 1 sink at face).
 2 Reach: PASS by geometry -- every macro <=~270 um from the band; checked again on the gate PNG.
 3 Fanout: PASS-pending -- v14 (2ac1ffeb7) census left 1 reg (ks_valid 36) + 2 comb nets 41/36;
   1e057b7bf bounds those phase/config cones; gate textbook_lint census is the check.
 4 Depth: PASS -- mapped depth 520 ps (v14) < 600 ps; registered one-hot head selects.
 5 Storage: PASS -- event/start payloads in 84 SRAM 64x16 macros; no runtime-indexed flop tables.
 6 Floorplan: PASS -- 43.2 lattice, >=20 um channels, std 40-60% in a full-width band, aspect 1.44.
 7 Clock: gate-checked -- ck/rst_n W pins at the band centre; spread <=80 TT+FF required; io_hold 0.03.
 8 Schedule: PASS -- static, no added edges (per Codex v11-v16 proofs; MU AR92/MTP22/faults/mutants).
