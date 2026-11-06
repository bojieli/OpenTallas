VMS clock C: candidate, ordinary physical gates pending

Current flow: flow-20261106-an-hbm. Immutable input capsule:
intel1:/srv/opentallas-scratch3/claude/codex-hbm-vms-1105/vA_i2
(original epyc4 die-hbm-75/eco/eco_f512rp/i2 copied in full).
The capsule 4_cts.odb is a routed ECO seed, retaining the measured A regional
clock topology. Existing recovery i1/i2 and all their clock-freeze checks remain
unchanged.

Recovered i1 reached TT +55.49 ps, FF +0.28 ps and DRC0, but slew37/35.
One of those residual slew points is frozen clock wire14308/A: TT536.32 ps
and FF531.92 ps versus320 ps. Its source wire14309 is at133.380,161.730;
wire14308 is at80.514,307.260. The198.396um endpoint Manhattan leg crosses
two abutting SRAMs, making a direct midpoint illegal.

The reviewed construction inserts exactly three positive BUFx12f repeaters
at x35.64 and y161.73/235.17/307.26 in the west corridor. Segment lengths
are97.740/73.440/72.090/44.874um. It explicitly removes only the obsolete
net14308 wire in this new clock baseline, preserving all other old clock routes.
The construction uses the ODB create/connect primitives used by the existing
density-clock constructor; no RTL is changed. All11,837 clock endpoints retain
exact native input-root and polarity membership. Three buffers were placed
exactly at the reviewed sites; maximal legalization movement0.3um. The new
functional cell count55808 excludes filler and stays below150k; density knob.45.
Added data cycles0. Existing registered faces/reset logic and native pins remain.

Read CLOCKC_GEOM_REVIEW.md and vms_clockC_review.png before replay. Run
construct_clockC.tcl in a separate candidate copied from the immutable seed;
never run it against the active A recovery or a data-ECO pass. It intentionally
creates a new clock baseline. Then run run_clockC_baseline.sh through ot-run.
The driver resumes do-route/do-finish and uses the released post/signoff runner,
then actual routed LEC. It does not rerun synthesis or the baseline comparison.
All full timing/clock/DRV/DRC/PG gates remain ordinary. Final abstract adoption
also requires actual routed PG/OBS and layer footprint, not stage2_4 intent.

Private candidate:
intel1:/srv/opentallas-scratch3/claude/codex-hbm-vms-1105/kits/vms_clockC
Admitted wrapper: intel2 client3752553,48GB/8threads/disk20, prioritydie.
Log: intel2:/srv/opentallas-scratch2/claude/codex-hbm-vms-1105/log/clockC.otrun.log
Status: candidate only; no main merge or adoption until physicalPASS+routedLEC.

Rehome phase correction: original global route reached zero overflow then RSZ-0074
because repair_design saw only 3677 new routes against a 50010-net fixed seed.
Use existing SKIP_INCREMENTAL_REPAIR=1 only for this clock-construction baseline.
No clock-freeze check is relaxed. Ordinary final signoff remains mandatory; any
subsequent data ECO freezes the new clock topology and retains all normal gates.
