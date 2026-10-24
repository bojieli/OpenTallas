# DIE-STA lane (claude/die-sta-1024, wt localhost:~/wt/die-sta)

## Current step
Started 07:10 PDT. Surveying existing die STA (gen_phys.sta_die_tcl / run_die.sh flat+etm at TT/FF) and OpenSTA be771a0
(write_timing_model present in fleet `sta` 3.1.0 and ORFS openroad). CP1-R10 r10 kits on epyc3 at CTS (not routed yet).

## Plan
1. tools/die_plan/die_sta.py: abstract mode (per-partition write_timing_model ETM at SS/FF + seam wire RC) and flat mode
   (stitched 6_final.v + per-instance SPEF), SS setup / FF hold, 60/25 ps uncertainty.
2. Validate abstract vs flat on CP1 r10 pair once CP1-R10 has routed kits.
3. Flat capacity: synthetic N-copy stitched replica of a real routed partition on a 1 TB host; extrapolate to 400 x 400k.
