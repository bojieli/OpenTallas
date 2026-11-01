# Actual R2 placement review

Personally viewed auto_geom.png at 2026-11-01 15:29:46 PST. FAIL: actual reset registered hop461.11um,486captures beyond405. Source rst_s[1] centre(368.442,103.005), predecessor rst_s[0](368.064,103.815). Own netlist traversal finds4324reset captures, bbox(5.13,4.455)..(382.752,168.345), centroid(167.61418,82.34981);486overreach captures bbox(5.13,4.455)..(61.182,168.345). This is R2's own placed DB, not transplanted R1 geometry.

Actual388.8x172.8,fill.2599,empty.2955,col_v.596,pinregp90/max9.05/51.07,zero unregistered;25719clock sinks before CTS. Image shows intact dense N/S boundary rows and distributed internal logic without a new macro wall. Preserve AUTO aspect2.25/r2r/r2r_count/GRTNOTRUN failures. Clock reach at zero fixed clock cells is pre-CTS information only. No CTS/P&R advancement until legitimate measured correction, own planned LOOK and actual corrected geometry.

Original placement is immutable: epyc2 and intel1 codex-bksel-r2-place-1440/kits/dsdv_bksel_c_pipe_ab_r2P/run/results/asap7/kl_dsdv_bksel_c_pipe_ab_r2_1131/base/3_place.odb SHA969fdb3e7d0f6b3aa58152d20eeb87706ee3d04d424af1e9588a6c0b34eb04df. Normal source whole-kit R2EQ receipt25ca9eefe remains valid only for exact source inputs; geometry failure is not waived.
