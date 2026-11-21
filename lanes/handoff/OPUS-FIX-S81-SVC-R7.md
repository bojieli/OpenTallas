# OPUS-FIX-S81-SVC-R7 handoff (started 2026-11-21 08:3x PST; newest first). Succeeds OPUS-FIX-S81-SVC-R6 (read its handoff for bind history).
Nothing signed or exported yet.

## 11-21 08:5x PST STATE
COORD RULING 08:3x: hi4 only in J7; other 15 svc split types -> J8 (cut between port windows per type, lo 3-way or more into att <=400k each,
hi t1/t6 plan FT corridor row, tool-generated, private bind gated, to S81-J6-ASSEMBLY-R4). svc_* hold stays until hi4 signs off.
LIVE (waiters needed):
- chain10h epyc10 PID 1746572 (bind_hi4x/chain10h.sh; posts as OPUS-FIX-S81-SVC-R6): split -> elab -> strict bind -> LATCHECK -> STATE -> att kit prep/place/route (KSTATE).
- chain_rest8 epyc8 PID 833298: waits epyc10 STATE green -> rest part svc_hi_dsdv_svc_rs__t4 kit place/route (KSTATE_REST).
  Both under /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r5/bind_hi4x.
POSTED to R4: hi4 J7 row re-post (rows file lanes/handoff/OPUS-FIX-S81-SVC-R6-J7-rows.json, base plan_svc_hi4_x_epoch.json 5edd9560, gated on chain10h).
REACH>405 svc 8: real (kit S0 = input pin; die check reads regs_um[0]). GEN epyc10 opus-fix-s81-svc-r7/reach/gen/mkft_svc_s1.py {IN} {OUT}
  (ft_add_station +1 S1; 8/8 closed on J7 v5, 6 lanes +1/+2 cycles). Handed to R4 for the next candJ7 gate (no private copy: 52 GB, 96% disk).
Lane clone: epyc10 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r7/repo (main 197076cf03; the GEN imports from it, keep it).
NEXT: on STATE -> fix or watch KSTATE/KSTATE_REST; sign-off read (DRC 0, TT >= -42, FF hold >= 0, LEC; post-hook CTS); export both parts. J8 re-solve of 15 types.
