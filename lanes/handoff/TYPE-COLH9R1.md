# TYPE-COLH9R1 (2026-11-14 04:3x PST)
Target s81/col_h9_r1__t1__cl49d7a23e (about 40 pv variants in kit_wave items, none has ever passed GRT; all earlier attempts classified grt-overflow).
OVERFLOW MAP (pv47efee8f, epyc10 .../items/col_h9_r1__t1__cl49d7a23e__pv47efee8f/gen/*/run): outline 1442.88x1226.88, 81 macros, 323k blockages, 97k nets, GRT 30 iter (1h49) fails. Final table: total congestion 26909, 25574 of it M6 horizontal (max H 12), M4 H 820, M5 V 463, M7/M3 ~0; usage only 10.4 percent overall so it is local. Iteration-5 report: 308 of 337 hot gcells sit in one strip x 600-900, y 1050-1200 (top edge), 320 of 337 have capacity 0 (blocked tracks, usage 1 each, nets 1494xx). So it is a blocked-capacity strip near the top edge on M6, not global density. Routing window M2-M7.
FORMS (private run-item, B3v plan, a5 spec + gen_env, gen host epyc10, specs intel2 ~/type-s81-colh9r1/{fa,fb,fc}, work /srv/opentallas-scratch2/claude/type-colh9r1/<k>), pv47efee8f:
 fa OT_CONS_KIT=1 UTIL 0.4 MAX_LAYER M7 (density down)
 fb OT_CONS_KIT=1 UTIL 0.5 MAX_LAYER M9 (higher ceiling)
 fc OT_CONS_KIT=1 UTIL 0.3 MAX_LAYER M9 (both)
 outline growth: not launched (per-type outline change fails plan validation, same as TYPE-COLH9P5/T29; needs DIE-S81-92 plan change).
