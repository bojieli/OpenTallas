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
