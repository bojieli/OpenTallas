# COL-SNAP-BUILD (S81 snapped-plan private builds) 2026-11-14 08:10 PST
- Plan: B3v plan + ft_nudge.snap_offgrid over the 37 ledger types (181 stations, 198,902 bits, 0 fallback) = epyc10 /srv/opentallas-scratch2/claude/col-snap-build/plan_snapped37.json (sha 454b695a...), installed in src overlay src_b3v_local (B3v/src + main ot_dp_clk_landing LOCAL).
- 29 run-items (all of p2/p3/h10_r0_p1 + svc_hi rs t1 except P1 family [6 types, TL-COLH9R0P1 builds A=pv697f40c9 and B=pvf9acce4c] and P2 fc/fd [cl0045af7b pve183b536, cl9f71e63d pvef55eb84]) launched on intel2 ~/col-snap-build/<short>/spec.json, log run.log, work epyc10 col-snap-build/<short>, private identity registry KW_IDENT_FILE=~/col-snap-build/ident.json (duplicates stop as DEDUP after gen/lint).
- Next: per surviving identity, run route myself after geom (ot-run run_kit.sh route); gates DRC0, TT setup >= -42, internal hold >= 0; AUTO-RESIGN row crediting members.
- Taking col_h9_r0_p3 (all variants) per COORD from ended TL-COLH9R0P3.

- 2026-11-14 08:35 CANCELLED all private builds (COORD: B3x2 adopted). Role now follower of wave rows for the 37 ledger types + p3. Asked KIT-OPS-3 to drop the COL-SNAP-BUILD hold_items.
