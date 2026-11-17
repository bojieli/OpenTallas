# HEAD-CTL (Sonnet, child of HEAD-TYPES-R2) 2026-11-17

Cause (NF15c hd_ctl, TT -96.09 / internal FF -9.59): u_core.u_logic.g_ms[*].g_h[*].u_h/q (tap clk_t4, 469 ps) -> ~1 mm wire + 6-level XOR/OR reduction -> single flop mchk_cpy (tap clk_t50, 1230 ps). Structural reach problem.
Fix (already built by Codex, r490): claude/head-ctl-mchk-local-1116@2ab82cffae0, opt-in MCHK_LOCAL param, per-word local mismatch FFs next to sources then OR9 (+8 FF, 0 added cycles, SAT miter on 81x3 SUCCESS, dropped-word/extra-cycle mutants detected, normal gate GREEN 1/1). Enabled in kit wrapper via .MCHK_LOCAL(1) on u_core (default 0 in source).
NF15c vs NF15d2r1 for hd_ctl: published wrapper ot_s81hd_ctl.sv byte-identical, source_sidecar identical, core_pins identical, partition plan identical except sink_bins_file tree-name path. No rebuild needed. (My own d2r1 regen script d2r1_gen_ctl.sh in head-types-r2/ was cancelled unstarted.)
Live: E7 /srv/opentallas-scratch2/claude/head-types-r2/mchk_local/kit_hd_ctl, unit oth-ubuntu-4092918-1794899895, log ~/head-types-r2-logs/mchk_local_grt.log. Pre-GRT TT +1.53 TNS 0 after 18 repair cells; FF pre-GRT repair running (20848 ends, -108.19 parent-side, gate PASS). geom_review PASS-COND.
Next: route goal on the same kit after GRT screen, r417 HEI pass if only internal FF fails, LOOK at layout, ffht_export.sh to rtx-pro + AGIdock.
Do not restart the E7 unit.
