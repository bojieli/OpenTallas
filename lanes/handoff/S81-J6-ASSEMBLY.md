# S81-J6-ASSEMBLY handoff (started 2026-11-20 17:50 PST)

Takes over J6 build/prove/apply from S81-DIE-R4 (cut 11-21 13:00). S81-DIE-R4 keeps J5 ops (post-apply bind, leaf reps, svc_rs MPL watch, holds).
Inputs read: lanes/handoff/S81-DIE-R4.md, FABLE-CLOSURE-STRATEGY 17:30 + 15:15, FABLE-PD-S81-1100.
Hub dir: intel2 /srv/opentallas-scratch2/claude/s81-j6-hub (logs, scripts).

## J6 item status (priority order)
1 source+tools adoption (main source, hwin 8e20268b5d83 + reach row, RIP1 + lepe rows 1-4; tools re-pin 8e9cdd615c/ecd0239bd5/f02ccd50eb/25fc65d0cb1): OPEN
2 monitor-pin rows (S81-MONITOR-PIN-1745, 29 types) + item 9 relays (fallback 405 die-top hop): OPEN
3 donors f0_q, rom, r1_frame, t31, vp_sr SRAMREG (+real ho sites, VP cycle in compiler table, 79 types): OPEN
4 col masters routed w/ launch-leaf latch: OPEN
5 leaf reset legs (reset_leg_plan.py on J6 bind): OPEN
6 per-lane spread rows + slice C finish leg (S81-SLICEC-R3): OPEN
7 bk_sel rows (OPUS-FIX-S81-BKSEL-R3): OPEN
8 svc manifest delta (FABLE-FIX-S81-SVC-R3): OPEN
9 leaf class rows (S81-LEAF-CLASS-1730) if green else J7: OPEN
10 lockup rows only after LOCKUP-STATION-1130 proof2 re-solved taps: OPEN
Gates: regression census vs J5 (monitor pin dist, hops, reset legs); private strict bind 0, LATCHECK, G0 no new over J5; apply.

## 11-20 18:30 state
- Work root epyc10 /srv/opentallas-scratch2/claude/s81-j6/ : clone/ (lane clone, main abfa72731be0 = rt current), mk_tree.sh (rsync link-dest of
  J5 tree kw45/s81_j5_existing_clock_r4_1120/tree, tools from rt/<sha>, TOOLS_RT_SHA file), adopt_rtl.sh, gate.sh (rt_pin; strict --all-gaps,
  LATCHECK + latcmp vs J5 gate_r5_repair, G0 + g0cmp vs J5, PRE), gates/<name>/, logs/gate*.log.
- treeA = J5 plan/rtl + rt abfa727 tools (tools control) -> gate A_tools_control RUNNING (epyc10 ot-run 108 GB).
- treeB = treeA + rtl adoption (adopt/classify.tsv: 76 MAIN_OLDER files -> main, 115 main-only added, 24 J5_PRIVATE overlays kept;
  vp CFX is opt-in/off, so the J5 vp overlay stays) -> gate B_rtl_adopt QUEUED.
- Donor deltas (plan_delta.py format) epyc10 s81-die-r4-donors/<d>/j6_delta_<d>.json: rom 60 types, vp_sr 79 (+manifest define/reproof), r1_frame 1
  (needs schema 8e9cdd615c: in rt), t31 1. f0_q: J5 dir plan_j5_f0_q_date_private.json / gate_f0_q.
- epyc8 j6_lockup: hop.tcl client cancelled (input ODB deleted), 2 echo-LEC waiters killed (PIDs 95864/96446); r1 midpoint masters not routed (stop list).
