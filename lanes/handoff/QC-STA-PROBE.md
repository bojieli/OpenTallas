# QC-STA-PROBE handoff (Opus 5.5, child of QC-ALLFIX, started 11-24 21:05 PST). Report to COORD, cc QC-ALLFIX.
Job: first st_a kits on a plan with both st_a fixes (r10 btab seat y 587.52 + PG-EDGE-HALO-STA pg_halo_um), to sign-off.
Work dir: epyc2 /srv/opentallas-scratch3/claude/QC-STA-PROBE (bin/, in/, rows/, tree/, logs). OT_LANE=QC-STA-PROBE.

## Plan
- Probe plan = C1m 851b964db1f5 + FIX-RELAYCOPY (fixM.sh, = C1m-rc) + PG-EDGE-HALO-STA ac4b82116adb (QC-STA-CLK epyc2 rows/)
  + RC97-BT2 regenerated on C1m (main generator d89536ec63ca), merged by plan_merge3 (rt fc44871c3df0): rows/probe_m3.json.
  One plan for both probes (RC97 touches only st_a_v2 + st_b_v2 via hook).
- Guard: compose_drop_guard prev=C1m, rows relaycopy/pghalo/rc97 -> rows/guard_m3.log.
- Types: v1 sle_st_a_v1__cl67389ecd (not the 2 RELAYCOPY types), v2 sle_st_a_v2__pv30dda31f__pv88773f93 (E5). No live kit on either.
- Tree: ot-tree-fork of epyc2 QC-STA-CLK/tree (C1m fork) -> tree/, + RC97 overlay (epyc10 QC-RC97-BT2/c/ov: btab RTL, bind hook, views).
- Bind: own FULL strict bind (R8 loop + LATCHECK, bindrun_l pattern) of the probe plan on epyc2 = bind of record; composite
  (scoped + C1m-rc full bound top) is not valid for v2 (RC97 changes st_b_v2 RTL via hook).
- Kits: kit_wave.py private-spec (on intel2) --rt 5494914b27ab --goal route --ab OT_PROBE_THROUGH=1, run-item systemd unit.

## 21:25 PST state
- Plan 9292a6474e9b built + guard PASS (0 silent, 2 intended RELAYCOPY); verify.log: 11/11 st_a y 587.52 + 83 pg_halo_um; PG re-census on bt2 LEFs 83/83.
- Posted PLAN + FOLD (to QC-RC97-BT2) 21:21.
- Full strict bind: epyc2 unit oth-ubuntu-1057584-1795584032, log $W/bindP.log (ends BINDP_DONE rc=N).
- Auto-launch: intel2 user unit qcstaprobe-autolaunch (/srv/opentallas-scratch2/claude/QC-STA-PROBE/autolaunch.sh, .log):
  on BINDP_DONE rc=0 it runs private-spec + run-item for E5 v2 then v1 cl67389ecd, posts LAUNCHED with units; on fail posts BIND FAIL.
- Verdict posts must say whether the worst TT path is an unstaged origin-to-pin hop >405 um (QC-ALLFIX 21:2x; RTX-ALL row goes to C1n, do not wait).
- Next: GRT post, CTS skew post (POST-hook report), sign-off verdict (DRC, TT pair skew, TT/FF). W5 slw_st_a_v2__clf4365a62 on same bind if E5 clears GRT.

## 22:48 PST state
- Bind pass 1 R8_STALE; refresh REFUSED by tree-write guard (relative table via symlinked launch view). Cancelled, resumed with
  bin/bindP2.sh (table = $T/$r8t absolute + --root $T): R8 OK f88f310ea379 -> 04648b1e3a08; unit oth-ubuntu-4077160-1795589180, log bindP2.log.
- Launcher (rt 6e9705f7fe67, +OT_TAP_ESCAPE_CLEAR_UM=0.30) now needs "LATCHECK complete" + BINDP_DONE rc=0 in bindP2.log.
  An empty bindP2.sh run (22:42) made a false pass; private-spec refused BIND_STALE, nothing launched.
- r8_refresh symlink fix on main: handed to QC-ALLFIX to assign (not this lane).
- Lane waiter: localhost scratchpad wake.sh <baseline lines> on posts/QC-STA-PROBE.md.

## 23:54 PST state
- Full bind (bindP2, rt 5494914b) FAILED 23:51: EMIT 290 (281 "START raw reset rr_tN has no registered wavefront driver", 9 RSTREP), 0 on st_a; likely C1m-wide (posted).
- Now: SCOPED-TOP strict bind (rt 6e9705f7fe67, probe_top, QC-STA-CLK s4 form) of E5 v2 + v1 cl67389ecd + W5 on epyc2: bin/scopedP.sh,
  dir s6/, log scopedP.log, unit oth-ubuntu-2827406-1795593183. Launcher now watches scopedP.log, --bind-out $W/s6/bind; W5 held to E5 GRT.
- epyc2 / at 91% (321G free); QC-STA-CLK runs its kit builds on epyc10 (roam).
