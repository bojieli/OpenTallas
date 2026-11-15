# TYPE-SLICET30 (S81 slice_station__t30__cl1653104c) 2026-11-14 ~12:15 PST
Failure b8f6d5a6e4cf: GRT-0116 at end of full GRT, 30 iters, near miss only (total congestion ~76 gcells, max 1; M3/M5/M7/M8 tiny; usage <4%). No -allow_congestion in kit (OT_GRT_CONGESTED_FAIL not present in this kit).
Forms (copies on epyc10 /srv/opentallas-scratch2/claude/typeslicet30/{a,b,c}, ot-run queued on epyc10, logs intel2 ~/typeslicet30/{a,b,c}.out):
 a: resume from 4_cts, GLOBAL_ROUTE_ARGS -allow_congestion
 b: PLACE_DENSITY 0.4 (re-place from 3_*) + -allow_congestion
 c: PLACE_DENSITY 0.35 + MAX_ROUTING_LAYER M9 + -allow_congestion
Original kit: epyc10 .../items/slice_station__t30__cl1653104c/attempt_19/gen. State: all 3 queued for memory (32 GB, epyc10).
## t37 (6152f8b9f52b, 12:12, attempt_3 on epyc9): same near-miss (170 gcells, max overflow 2, usage 6.5%, GRT 2h19, peak 27 GB). Form a copy epyc9 /srv/opentallas-scratch2/claude/typeslicet37/a, ot-run client PID 810325 queued on epyc9, log intel2 ~/typeslicet30/t37a.out. b/c not launched (COORD said a first).
## t30 state: a queued epyc10 (282150) epyc2 (402139) epyc9 (402140); b/c epyc10. Waiter t30_wait3_container_typeslicet30.sh (fires on container admission).
## 15:42 t30 SIGNED via form c (epyc10 typeslicet30/c). Archived rtx-pro+AGIdock, AUTO-RESIGN row, RESULT + KIT-OPS-5 ask posted.
Winning form: PLACE_DENSITY 0.35, MAX_ROUTING_LAYER M9, GLOBAL_ROUTE_ARGS -allow_congestion, 56 GB. Memory note: 32 GB cap + epyc8 earlyoom killed t28 c / t24 c in hold repair.
Open private forms (kits /srv/opentallas-scratch2/claude/typeslicet<N>/<form>; logs intel2 ~/typeslicet30/): t8 a,b,c; t37 a,c; t28 a,c; t24 c; t52 c (queued epyc9 1987263 / epyc10 1987264). First sign-off per type wins; cancel the others by exact PID (docker stop by name for running containers).
## 19:25 successor: t28 form a already dead (exit 143, ot-heavy-stop --match matched 0 scopes on all hosts, nothing to cancel). Live: t8 a/b (epyc10/epyc8), t8 c (epyc10, 10 min old), t37 c, t28 c, t24 c (epyc8), t52 c (epyc10). Waiter ~/typeslicet30/t30_wait13_results_typeslicet30.sh (log ~/typeslicet30/wait13.log) logs SIGNOFF lines and stops t8 a/b on t8 c SIGNED. FABLE-HARD-S81 19:05: t28/t36/t27 rebuild on B4L4 at adoption, no more private forms on old bands.
## 19:58 (resumed after 19:43 crash) waiter 2953517 still alive. t52 c ended exit 2: do-5_1_grt Error 247 with peak mem 31.75 GB (kit cap 32 GB, not the 56 GB intended) = likely memory kill in GRT, not a design verdict. Live: t8 a/c (epyc10), t8 b, t24 c, t28 c, t37 c (epyc8).
