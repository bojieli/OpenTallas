# FABLE-S81-CORES (Fable review, last 2 S81 cores; successor of FABLE-REVIEW-CORES), 2026-11-14 19:2x-20:2x PST
Reviewer lane: diagnosis only, launched no build. Full text of both findings: lanes/posts/FABLE-S81-CORES.md (2 READY lines, 20:1x).

## dsdv_gunit_l1f_bf (owner TYPE-GUNIT-L1F)
- Cause of -208/-251/-317: one forward address copy; W-face flop -> dec64 g_dec[8] placed at x 345 -> back to lane 0 at x 36 (681 ps wire, 254 ps logic).
- FWPIPE builds are all dead: ba0_fwp/ba0_fwps2/ba1_fwp killed by earlyoom on epyc10 16:32 PST ("Error 241", infra); bf form c GPL-0307 (guide cone cut by the new stage + F1-size exclusive boxes over the centre).
- Form to build: FWPIPE (a769ba16f6) on the gunit_g3 kit (432 x 216) with guide tools/gf5_locality.fwpipe_g3.tcl (epyc7, epyc10 fable-review-cores/tools, md5 ad10dc45283d). Dry-run membership checked; not placed.
- Open: internal vs port FF hold split; g4 (FWDOWN, epyc10 unit oth-ubuntu-4102104-1794706270) in GRT iteration 12/30, pathfinding.

## dsdv_bksel_q (owner S81-CORES-2)
- Cause of the 165 M5 markers: pk2 N/S M5 pins (0.192 pitch) under/next to the parent M5 strap ends on the shared 4.32 grid; also pk2 has 0 M5/M6 PG vias.
- Fix: branch claude/fable-s81-cores-pk2-pg-nsesc-1114 @ 2831874a (macro grid native_pg_M5_nsesc, halo {0 4.32 0 4.32}); PDN-only check 180 -> 0 strap boxes, 0 -> 3698 vias. READY to ROOT-MERGE-63.
- m7pg (epyc8 unit oth-ubuntu-5128-1794709945) in DRT iteration 1 at 20:15; S81-CORES-2 waiter covers it. Structural full build not launched (theirs).

## Evidence
intel1 /srv/opentallas-scratch2/claude/fable-review-cores/s81cores_probe: b/b_final.csv, c/c_gp_failed.csv (positions), an.py, pdn/go.log, gt/t.log. No waiter of mine is armed.
