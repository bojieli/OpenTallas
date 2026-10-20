# hcoll_fj2_r128u2 (HBM-COLLQ3-5, 10-20) -- successor of hcoll_fj2_r128u: SAME RTL (e6846a038), ports, edges and literal geometry; ONLY change OT_RST_COPIES_MAX 32 -> 16

Why: r128u actual post-GRT ODB (de8a55d4f, results/rtl/hbm_coll_fj_1019/codex_native_1020/r128u_postgrt_native) showed the pin_reg_split ot_prs_ff clones add real DFF RESETN loads (+13 q3 / +10 q2) to the original 24-load reset relays -> 37/34 (q3), 37 (q2) > 32. With reset leaves capped at 16 the worst leaf is <=16+13 = 29 <= 32. Reset still lands in 2 registered stages at the S face (OT_RST_LAND_STAGES 2), same release edge/polarity; more KEPT leaf copies.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input/output registered (RTL pin flops + pin_reg_split), reset 2-stage landing.
2 Reach: PASS -- tile Manhattan 174.96 um < 405.
3 Fanout: FIXED -- pre-hook mapped census e6846a038 max32 (q3 8786 / q2 8803 drivers); reset leaves now <=16 + clones (<=29). Post-GRT native census on this gate's ODB REQUIRED before review.
4 Depth: PASS -- q3 351.7 ps / q2 268.4 ps mapped.
5 Storage: PASS -- flow table in ot_sram_1rw_128x64; assembly 1536 b + metadata < 2 kb.
6 Floorplan: PASS (pin/lattice-bound) -- stock SRAM R0 (43.2,43.2), 103.68x71.28 (1.45:1), full-width S std band 40.7% density, global fill 37.2% (fill_reason in spec), pins <=4.167/um.
7 Clock: single scalar root at S beside register mass (~3k sinks); spread <=80 TT+FF measured by this gate; io_hold 0.03.
8 Schedule: PASS -- 0 external edges changed -> 0 cycles DS/Qwen.

Open HOLD carried from r128u: hold-fix bind-before-protect PG bug (protected PG-unbound newborn cells, r128u 612/620). Fix 364197f30+a114c3745 (codex/pg-protect-birth-1020) NOT on origin/main at 10-20 02:30; ROOT b2fef6b6a unmerged. Gate uses origin/main helpers (tools/ref_tile, closure_loop, common_flow incl. 67cb1acc7 standard-mode PG bind). CRITICAL prefix -> COORD-REVIEW-QUEUE, no REVIEW.json / submit.
