# FABLE-FIX-S81-SERDES-0600 handoff (Fable; owner of the 11 S81 serdes types from 2026-11-20 01:25 PST; successor of -0000)
Read lanes/handoff/FABLE-FIX-S81-SERDES-0000.md first (root causes, rows, tools). This file holds only what changed since.
Gate: R-MINIMAL (route DRC 0, TT >= -42 at 833 or sign at up to 1000 ps on the same routed DB per SIGN-PROFILE-0400, FF hold >= 0, bind + LATCHECK).
11-20 owner rules: 300 um placed-hop cap default (half-cycle hops ~200), registered memory reads default, one S81 plan event per day (cut 14:00 PST -> S81-DIE-R3).
Dirs (mine): intel2 ~/fable-fix-s81-serdes-0600 (client logs, L.sh launcher), hosts /srv/opentallas-scratch2/claude/fable-fix-s81-serdes-0600
(epyc9: sta_run.sh sta_census.tcl geo*.py hop_run.sh; epyc7: lec_run.sh hop_run.sh; epyc10, intel2: hop_run.sh). The -0000 dirs stay (R1 lives there).

## State 2026-11-20 01:55 PST
No serdes type signed off. Nothing exported.

### Live units
- R1 serdes__t13 proof (epyc7, unit oth-ubuntu-564596-1795161073, kit .../fable-fix-s81-serdes-0000/R1/serdes__t13/gen/serdes__t13): in global place
  (epyc7 load 650/96). -0000 waiter wait.sh still armed on intel2 (posts to FABLE-FIX-S81-SERDES when the client ends).
- Queued behind fleet memory (every host admits 0 GB at 01:50), client logs intel2 ~/fable-fix-s81-serdes-0600/*.out:
  lec-R1 (advisory LEC of the R1 synth netlist, epyc7, out .../fable-fix-s81-serdes-0600/lec_R1);
  sta-h23_grt (class census of the H23 5_1_grt.odb, epyc9, out .../sta/h23_grt);
  hop-t13h25 (epyc9), hop-t15p (epyc10), hop-t14w, hop-t1bw (intel2 = "localhost" for ot-run): placed-hop scan at 300 um
  (tools/precheck/placed_hops_or.py + hop_sum.py class table), out .../hop/<tag>. These measure the TX side too.
- Not mine: H23 (epyc9, GRT hold repair), H25 (epyc9, CTS), T15P (epyc10, 4_cts), wave b05c98f7919 serdes kits (H22 rck form).

### Facts read today (V)
- H23 kit log (its own run): OT_STB_SPAN rck span 89.0 PASS; GRT TT setup_est -178.27 before repair, TT repair at GRT rc 139 (crash), hold ws -54.57
  (1048 ends) entering GRT hold repair. So H23 at GRT is no better than H22 (-179) by the kit number; which class limits it is what sta-h23_grt answers.
- Pre-place LEC is dropped family-wide under R-MINIMAL (run_kit.sh lec_preplace.off); the R1 "LEC skipped" is the async watcher only. lec_run.sh runs
  lec.py on the kit read-only.
- J4 r2 binds on plan_j4e 9780ae146139 (intel2 ~/s81-die-r/build_j4_r2.log), with the 54 serdes rows.

### Next
1. Read the queued results; decide the rck form row (H23 vs H22 vs H21 star) from the census, post it before the 14:00 cut.
2. TX side rows from the hop scans (coll_i0 -> u_enc -> u_txl -> u_ptx), 300 um cap; existing opt-ins: OT_S81_SERDES_TXL4 (+2), TXPIPE (+1), tx_pin N=3.
3. R1 to GRT TT/FF and route; t15 proof from the J4 bind; family builds (run_kit goal route); export.
