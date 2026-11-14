# TL-LEAFT62 (s81 ot_s81sl_leaf__t62) 11-14 04:5x
- History: a4 (plan 81d1, epyc7) placed, route 5c1cd98cc727 FAILED grt-overflow 54061 hotspot u_bound.u_ft_ft0_o_4 (structural). a5 (src_pgL PG-cap fix, epyc7) FAIL place RC=99 = ot-job spill infra (run_kit.sh not in store; KIT-OPS-4 patch merged). a6 (epyc8) INFRA landed_sidecar_aor3.json missing on epyc8 (only on epyc7). a7 CANCEL-SUPERSEDED, no relaunch yet.
- Action: private build of the a5 (src_pgL) kit, unsealed, pinned epyc7: kit /srv/opentallas-scratch2/claude/tl-leaft62/gen/ot_s81sl_leaf__t62, log intel2 ~/coord/tl-leaft62-run.log, goal route.
- If grt-overflow repeats at ft0_o_4: plan-level (ft street/pin spread) to die owner DIE-S81-92 with numbers.
