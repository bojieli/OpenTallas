# TYPE-LEAFHOLD (DIE-S81-92 C) 11-14
- Cap is NOT a fixed watchdog: hold_guard_grt.tcl OT_HOLD_MAX_HOURS (default 3) + OT_HOLD_STALL_WINDOW_S; FAILFAST-1 ends the build on the OT_HOLD_STALL marker. Per-item lift = item_env OT_HOLD_MAX_HOURS / OT_HOLD_STALL_WINDOW_S (KIT-OPS-4).
- Slow because: t44 viol 6444 ws -201 on 283k insts, 1100 buffers in 3 h (each re-routes GRT); t25 viol 332 ws -5.4 only. t44 lifting cap is futile (days); needs pregrt.
- Forms on epyc10 /srv/opentallas-scratch2/claude/type-leafhold: t44A/t25A = OT_PREGRT_FF_HOLD=1 guard 45; t44B/t25B = OT_HOLD_MAX_HOURS=24 + window 86400. Logs intel2 ~/coord/lanes/handoff/tlh-logs/*.out
