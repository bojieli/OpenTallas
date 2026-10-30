# DIE-QC-47 BTAB post-route repair (results only, 2026-10-30 11:41 PDT)
Start: variantC kit (= C terminal: 6_final.odb d3c9d212 / spef f9648ea0), diag metadata pins.json/sdc_lint.json, ft_* files absent.
Recipe: shared tools/die_plan/post_route_drv (prd_mk.sh, unchanged, main 16f2590f75f) + pass-local PRE_GLOBAL_ROUTE grt_pre_prd.tcl
(kit keep-offs/planned_rep already in 5_1_grt.odb; re-sourcing them crashes NULL). Staged: do-grt (ECO) -> LOOK -> route -> finish -> sign-off + LEC (chain_post.sh).
P1 hold margin 15 (kit), P2 hold margin 27 (sign-off FF hold uses 25 ps uncertainty; kit model 13.97 vs sign-off -2.59).
ECO census (render_eco.py vs 4_cts): P1 +340 bufs, P2 +1646 (1299 hold BUFx2); both 0 FF master change, 0 FF moved, 0 new cells in SRAMs.
AUTO-GEOM both: GRT 0 overflow, cells_on_macros 0; only fill/empty FAIL (standing fill exception). PNGs viewed.
Run dirs: intel2 /srv/opentallas-scratch2/claude/die-qc-47/btab/{P1,P2}; collect CHAIN.txt, signoff/signoff.json, lec_post/lec.json.
