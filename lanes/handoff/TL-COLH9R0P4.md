# TL-COLH9R0P4 (s81 col_h9_r0_p4__t1, 6 pv: cl8ef405e8 pv70731479/91095415/775e5cef/89bf360c, clcb2fbfe8 pv3544fb31/pvec137455) 2026-11-14 04:51 PST
- Cause of wave "RTL lint at gen": shared, B3v/src ot_dp_clk_landing.sv lacks LOCAL (see TL-COLH9R0P5 / TL-LEAFT14 posts). Not p4-specific. Plain names are dead (split into 6 pv in the plan).
- Private form A (plain), B1 src_pgL (has LOCAL), same spec as TYPE-COLH9P5 fa: specs ~/tl-colh9r0p4/fa_<cl>_<pv>/spec.json on intel2, run-item procs on intel2, work /srv/opentallas-scratch2/claude/tl-colh9r0p4/fa_* (gen host epyc9). Launched 04:51.
- Note: I ran one read-only git show in intel2 ~/OpenTallas by mistake (no changes).
- Next: follow to GRT/route; AUTO-RESIGN row on pass.

## 2026-11-14 19:3x PST successor recovered
- Live on epyc9 (all CPU-active, not hung): 4 route-stage items in run-item (cl8ef405e8 pv70731479/pv89bf360c GRT extra iter 25/30, clcb2fbfe8 pv3544fb31/pvec137455 iter 22/30, ~9.5 h in, openroad ~100% CPU 1 thread). 2 items cl8ef405e8 pv775e5cef/pv91095415 were re-run later (containers 5 h/4 h old, openroad glob/GRT live); earlier geom stage PASS-COND (geom advisory only).
- No relaunch. Next: when route/gate result.json lands, check R-MINIMAL (DRC0, setup>=-42, hold>=0), AUTO-RESIGN + export on pass; on 30/30 GRT overflow fail -> measured cause + structural change, Fable review via COORD (>2 rounds).
