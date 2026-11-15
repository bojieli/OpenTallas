# DIE-ROUTE-ABS-1 handoff (2026-11-15 08:2x PST)
## Scope
FABLE-CLOSURE-STRATEGY 07:3x lever 1: die clock cells placed under partition abstracts short against the abstract OBS in DRT.
## Layout
- epyc2 work dir: /srv/opentallas-scratch3/claude/die-route-abs-1/ (unit.odb = copy of probe_u201_b input, cut.tcl, unit_cut.odb, r_cut2/ = DRT on the cut database, run_drt.sh, kitcopy/ = HEAD p20nc_gate kit abstracts+tree.json for the tool dry run)
- repo clone epyc2 /srv/opentallas-scratch2/claude/die-route-abs-1, branch claude/die-route-abs-1, pushed to hub origin, commit 1e32ea5682: tools/die_plan/abstract_cutout.py, test_abstract_cutout.py (6 tests pass), die_trial.py kit flag --cut-abstracts-under-clock [MARGIN_UM] (default off).
## Proof (u201 crop, 3 steps like probe_u201_b: 3,276 -> 2,786 -> 2,800)
- cut.tcl: 600 of 606 clock cells sit under a tile abstract (tW1b7/8/9, tW1o7/8/9, tW2o7/8/9, all ot_s81hd_tile_p); 300 type-frame windows (cell +0.3 um); master OBS is frozen in odb so a clone master ot_s81hd_tile_p_cut (all 1,230 pins kept) replaces the 9 instances.
- r_cut2 running (DRT on cut db, started 08:00, step 0 expected ~08:30); result pending, posted as RESULT.
- First attempt (r_cut) did NOT change the OBS (frozen master) and showed 3,276 at step 0 = same as baseline; stopped. Do not count it.
## Tool
abstract_cutout.py cuts M1-M7 + implant OBS and the M7 PG pin over windows from kit clock/tree.json via die_trial.island_windows (one window set per type, plan abstracts and closed-view LEFs). HEAD full-kit dry run: 44,547 cells, 44,519 under a partition, 7,788 windows, 26 types, 0 inside hard cores.
## Class counts (cells under a partition outline, tree.json vs plan)
HEAD 44,519/44,547; KV (kvgeom5 plan_c, die-kv-route-1 p1 kit) 32,280/32,280; QC (s29 s3r kit) 127,101/127,106; S81 no kit tree found. These are cell counts, not DRC marker counts: only HEAD has a DRT unit run.
## Not done / next
1 shorts comparison from r_cut2. 2 if collapsed: READY, HEAD-100 die rerun with kit --cut-abstracts-under-clock (the kit regen takes ~20 min; or run abstract_cutout.py PLAN KITDIR on a copy of the p20nc_gate kit). 3 M8 pin-vs-PG ~400 markers: separate step, unassigned. 4 signed types: the closed view has real metal under the cell, the cut only fixes abstract-generated OBS; per-type site reservation (lever step 2/3) not started.
## Update 11:5x
- READY posted: u201 = 0 at step 3, 12.1 GB (8 thr). Recipe in the queue line. Branch claude/die-route-abs-1 @54c80d8f21 (epyc2 /srv/opentallas-scratch2/claude/die-route-abs-1), work dir epyc2 /srv/opentallas-scratch3/claude/die-route-abs-1 (r_c16r = proof, r_c16s8 = 12-step residue run, r_fine/r_c16/r_c32/r_base32/r_c16t8 = memory comparison).
- Memory: threads dominate (as built 9.4 GB at 8 thr, 24.4 at 32); fragmentation +30% at 16 boxes (527 rects), x4+ at 10,449 rects (110 GB at 32 thr); keep ot-run --mem >= 100 (jobs with 40 got exit 137 at RSS 41.9-62.8 GB).
- First cut had wrong MY-tile x (inst origin is the right edge); fixed (placed bbox). Earlier 383/41 numbers are void.
- Open: signed-type metal at the cut sites, ONE site template per type, other units/dies, S81 kit tree.
