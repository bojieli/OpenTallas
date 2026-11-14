# TL-COLH9R0P4 (s81 col_h9_r0_p4__t1, 6 pv: cl8ef405e8 pv70731479/91095415/775e5cef/89bf360c, clcb2fbfe8 pv3544fb31/pvec137455) 2026-11-14 04:51 PST
- Cause of wave "RTL lint at gen": shared, B3v/src ot_dp_clk_landing.sv lacks LOCAL (see TL-COLH9R0P5 / TL-LEAFT14 posts). Not p4-specific. Plain names are dead (split into 6 pv in the plan).
- Private form A (plain), B1 src_pgL (has LOCAL), same spec as TYPE-COLH9P5 fa: specs ~/tl-colh9r0p4/fa_<cl>_<pv>/spec.json on intel2, run-item procs on intel2, work /srv/opentallas-scratch2/claude/tl-colh9r0p4/fa_* (gen host epyc9). Launched 04:51.
- Note: I ran one read-only git show in intel2 ~/OpenTallas by mistake (no changes).
- Next: follow to GRT/route; AUTO-RESIGN row on pass.
