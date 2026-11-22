# OPUS-FIX-S81-COLROM-R6 handoff (started 11-21 23:1x PST; successor of FABLE-FIX-S81-COLROM-R5, Fable 429 until 11-28)
History: lanes/handoff/FABLE-FIX-S81-COLROM-R5.md. Lane dirs: intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-colrom-r5 (runitem_*.pid/.log, plans, tmp/);
new dir /srv/opentallas-scratch2/claude/opus-fix-s81-colrom-r6 (epyc9: srcJ8G fork).
GOAL: J8 col form. Rule: first col proof with final 5_1_grt.odb TT >= -42 and overflow 0 by 11-22 14:00. COORD RULING 23:3x: FAM-S81-COL-H9R0-R4 files the
single combined col set (seat fix + RELAY_MID_RE + keep rq + STAGGER [+ F seats if F closes]); I post my part to H9R0-R4 (done 23:4x), run D/E/F/G/H and
report their GRT. No separate col hand-off.

## Kits (all epyc9, work root .../kit-wave/s81/a9ed808a98d/private/<lane>/col_h10_r1__t1__cld01bb4ae_<stamp>)
- D _1121214130 (planD per-flop xd seats, J7 tools, 10 iters): post-hook CTS setup -81.07 (xd e7 xs_q -> u_u_e7_u_w ROM pin). runitem_d.pid.
- E _1121220326 (env OT_RELAY_MID_RE excl xd ROM stations, J7 seats, 10 iters): post-hook CTS setup +22.23, hold -63.79 pre-repair. runitem_e.pid.
- F _1121223001 (planD + 1212 south seats + 50 iters): placing 22:49. runitem_f.pid.
- H _1121231802 spec private_specs/OPUS-FIX-S81-COLROM-R6/..._1121231802 (planH = J7 plan + F 1212 seats; E RE; 50 iters). runitem_h.pid (intel2 3338988).
- G (COORD combined): fork J7 tree -> epyc9 opus-fix-s81-colrom-r6/srcJ8G (forkG.pid/log), then ot-build s81 col_h10_r1__t1__cld01bb4ae --tree srcJ8G
  (rebind on rt current) --ab OT_RELAY_MID_RE=<E> --ab OT_KEEP_WIRES="<wave list> ot_s81_rly:rq" --ab OT_RELAY_MID_STAGGER=1 --ab OT_GRT_CONG_ITERS=50.
- Cancelled: first G try spec _1121231436 (planF + E RE on J7 tools; inherits D -81 seats) at kit_rtl, ot-run unit oth-ubuntu-1270086-1795331713.
## Reads: CTS = 4_cts_post_hook.rpt; GRT = final 5_1_grt.odb only.
