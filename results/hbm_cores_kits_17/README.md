# HBM-CORES-KITS-17 (2026-10-29) — collect K13 / ring / HNX / keybuf; d16k kits

Auto GEOM = codex-hbm-k13-wave0830/tools/geom_check.sh (read-only, docker, GRT probe 50 it unless noted); every render viewed.

| kit | LEC | AUTO-GEOM | verdict |
|---|---|---|---|
| gq_land 4ff7e1/859e54/ab9f3b density26 | EQ | FAIL partial_face 1/1/2, col_v .78/.74/.85 (no GRT), W/M4 20.9 pins/um | FAIL (plan pins) |
| tkm idpin b05ff385dffe-_k13 | EQ | FAIL empty .56, r2r 492, relay_collapse 15 (GRT 0) | FAIL (outline ~2x) |
| tkm terminal a83e190d54f7-_k13 | EQ | FAIL empty .58 (fill .19) | FAIL (outline) |
| xload_cl2_bdring 0c99d1c898e0-_k13 | EQ | PASS (col_v .944 WARN GRT 0, S/M5 20.9 pins/um WARN) | PASS -> finish live |
| qw_dec 03c4f6c37aa2-_k13 | EQ | FAIL pin_reg_max 218 (rst_n only) | FAIL (reset sync not at pin) |
| xload_cl2_ctlx a49447763f6a-_k13m | EQ | FAIL fill .067 empty .72 r2r 640 | FAIL (outline) |
| argmax_sw_vm_r2 efae72feb6e7-_k13 | NEQ 548 | - | FAIL_PREFLOOR |
| xp_aq_tree13_fmt ed62ddb93a97-_k13 | NEQ 1056 | - | FAIL_PREFLOOR (f437090e0 probe) |
| dma_back_vp4_banks_cp d0c75d7ab20a-_k13m | NEQ 1 (wb_fill_epoch[4]) | - | FAIL_PREFLOOR (merged dup reg) |
| ring keep (codex 4efa91648) | EQ 26002 | FAIL r2r 414.5 (2) -> A2 ECO PASS r2r 383.56 GRT 0 | A2 -> finish live |
| keybuf _codexr4 | EQ 6336 | FAIL GRT ov 28886, col_v 1.92, fill .04, clock_reach 271 | FAIL (plan: W pins vs SRAM column) |

Ring A2 ECO: eco_move2.tcl moves the 47 ra_* N-face face flops with pin x<40 um by +18/-13 um, DPL (max disp 1.7 um).
d16k (f20e424277f7) kits: hcol_h0 PASS preflight; qctl/lanes8_11/sfustore V1 R-SRAM-ENTRY (mp/) preflight PASS; vmdel INFEASIBLE (deficit 2.23 um).
