# HEAD-WEST handoff (split from HEAD-R18, 11-23 19:2x PST)
Job: pick HEAD West form at GRT; nst4 kit if (b) wins; else next structural form. Every chain: --remap-base = parent plan (LANDREMAP fail-closed).
- Kits (intel2 ~/fable-fix-head-lep0n-1122/r18g_exact_continue/west-*; kit dirs epyc7 .../head_rp21z20NF15f_r17b/private/HEAD-R18/):
  - (a) wband prep_r18g_wband 014661a6ea33: hd_lep0N_w_1123175932 (unit head-r18-west-wband-grt)
  - (b) wch4b prep_r18g_wch4b f570eb1144eb: hd_lep0N_w_1123175934 (unit head-r18-west-wch4b-grt)
- Waiter: head-r18-kit-waiter5 (waiter3/head_waiter.sh) posts raw reads as HEAD-R18 + WEST WINNER + launches west-wch4b-nst4/run.sh if (b) first at 0.
- 19:2x: wband tap-pre GRT 0 overflow (12 extra its); wch4b still iterating.
- Local watcher: scratchpad west_watch.sh (background).
## 20:3x PST: WEST WINNER = (a) wband
- hd_lep0N_w_1123175932 5_1_grt: 0 overflow on clock (3,235 nets) + signal (134,451); TT setup ws +63.2 tns 0; FF hold guard +27.7, 0 violators (+201 buf). Render grt/congestion.png: red only over the hard cores; channels green/yellow, no hotspot at the old x60-110/y840-960 corner.
- No nst4 (only for (b)). wch4b hd_lep0N_w_1123175934 keeps running as a spare (in pre-GRT hold at 20:32).
- Unit head-west-wband-route (west-wband-route/run.sh): waits for the head-r18-west-wband-grt driver to end, then run-item same spec --goal route (sign-off+LEC), OT_LANE=HEAD-WEST.
- Waiter head-west-waiter (waiter_west/) still posts the raw reads for both kits.
## 20:4x PST
- COORD accepted wband. Required before it counts: classify the 5_1_grt.json hold -132.6 / skew 598 on the final stage db after sign-off; internal FF hold must be >= 0, and anything negative must be forwarded ring inputs only, within -568. Post the endpoint split + send the route render to FABLE-RC-ALL.
- waiter_west had an ls short-circuit bug (failed.odb* absent -> rc 2): fixed, now head-west-waiter2. Told HEAD-R18 its waiters carry the same line.
- head-west-wband-signoff-wait (waiter_wband_signoff/) posts the raw sign-off read + hold lines + render paths when head-west-wband-route ends. The lane still has to classify.
- Preview: pre-GRT FF OT_HOLD_GATE -86.4 (4205 ep, 1554 forwarded ring inputs, limit -568.4); post-repair FF hold guard +27.7, 0 violators; json -132.6 was read under TT vclk binding (likely IO/ring), unclassified.
