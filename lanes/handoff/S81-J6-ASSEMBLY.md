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
