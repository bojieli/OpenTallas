# TYPE-COLH10R1 (2026-11-14, lane for s81/col_h10_r1__t1__cl95b37463__pv799da6f8)
Failure: wave job 3a1d832b1e28 GRT ran 30 iterations (6h24), GRT-0116 final: total congestion 44569, M6 H 40502 (max H 13), M4 H 2008, M5 V 1387; usage 11.9 percent, so local. Same class as TYPE-COLH9R1 (M6-only strip over bf-wall macros).
Wave kit: epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/col_h10_r1__t1__cl95b37463__pv799da6f8/gen/col_h10_r1__t1__cl95b37463__pv799da6f8 (wave config: MAX M7, PLACE_DENSITY 0.5, OT_MAXWIRE_UM 100)
Private forms (copies under /srv/opentallas-scratch2/claude/type-colh10r1/<f>, resume.json, all with OT_GRT_CONGESTED_FAIL=0 and GLOBAL_ROUTE_ARGS=-allow_congestion; ot-run logs intel2 ~/type-colh10r1/<f>.log; mk script /tmp/colh10r1_mk.sh):
 fa epyc10: resume at GRT (reuses 4_cts), OT_MAXWIRE_UM 200, OT_FT_MAXWIRE_UM 220, MAX_ROUTING_LAYER M8 (was M7; COORD correction 12:xx, relaunched)
 fb epyc8: resume at place, PLACE_DENSITY 0.4, MAX_ROUTING_LAYER M8
 fc epyc8: resume at place, both
All three queued on ot-run memory admission (48 GB) 12:xx; waiting.
Evidence posted to DIE-S81-92 (queue, STATE): hot strip bottom edge x 660-900 y 0-120 over bf_col3_c (x 691-899 y 52-250) + bf16_half u_ha/u_hb; nets u_lpad_frame_int_i1 ring, frame_int_i1_q, lpl_*_r/w; ask R-COL-7 channel path keys + R-COL-8 station sites.
Waiter: scratchpad colh10r1_wait2.sh (ends when any ot-run client ends). All three still queued for memory.
Scope add (COORD): sibling s81/col_h10_r1__t1__cl95b37463__pvf724da2a (job 24d8f5106935 12:12 GRT overflow). Form fd = fa recipe (M8, maxwire 200/220, -allow_congestion, GRT resume), copy epyc10:/srv/opentallas-scratch2/claude/type-colh10r1/fd, log intel2 ~/type-colh10r1/fd.log, queued for memory. Move to fb/fc recipe if those win.

## Successor 2026-11-14 19:3x PST
All four forms RUNNING (not queued) in GRT: fa epyc10 (iter 80, overflow 75 falling), fd epyc10 (sibling pvf724da2a, iter 30, 310), fb epyc8 (density 0.4 maxwire100, log shows place), fc epyc8 (density 0.4 + M8 + maxwire 200/220): GRT CONVERGED at iteration 35, overflow 0 -> watch for route/DRC. Do NOT relaunch. pvf724da2a is a held COL-INHERIT sibling; fd only informs, sibling inherits from representative pv799da6f8 once any form signs.
Next: when fc finishes check DRC 0/setup/hold; if it signs, post READY/RESULT to COL-INHERIT + DIE-S81-92 with the recipe (density 0.4 + M8 + maxwire 200/220); export signed record to AGIdock + rtx-pro.
