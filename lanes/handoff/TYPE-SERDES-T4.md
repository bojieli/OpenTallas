# TYPE-SERDES-T4 handoff
- 2026-11-14 00:58 PST STATE: owns S81 serdes__t4 (hold after CTS, job 7ea098cfb625, structural hold stall ws -210 viol 5246) and serdes__t2 (GRT timecap 21600 s, job 8a83667edb33, e9eda32d41c). Work dir epyc9/epyc10 /srv/opentallas-scratch2/claude/type-serdes-t4/.
  t2A: copy of attempt_27 kit, resume start=grt from its 4_cts.odb, OT_GRT_POST_MAX_S=43200 (ot-run log intel2 ~/coord/tmp/serdes-t4/t2A.log, dir .../t2A/serdes__t2).
  t2B: same + resume start=place, PLACE_DENSITY 0.5 -> 0.4, POST_MAX 43200 (log t2B.log, dir .../t2B/serdes__t2).
  t4: attempt_17 kit was cleaned (reports only), regenerated on B1 src_pgL (7073a6b4a59, bind out B1/out) with gen env = die_gen_env + item_env (NONPORT_HOLD=1, CONS util 0.25), dir epyc10 .../W/gen/serdes__t4. Forms: t4A = +OT_PREGRT_FF_HOLD (pregrt_ff_hold.tcl installed by hand, config line) ; t4B = t4A + PLACE_DENSITY -0.1.
  First pass per type wins -> AUTO-RESIGN row.
