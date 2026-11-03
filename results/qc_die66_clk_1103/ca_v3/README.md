# DIE-QC-66/CLK count-aligned landed check on the v3 die clock (post-RED, windows plan 6331b0559332)
Proof: v3 kit (epyc2 die-qc-65-clk/v3, KIT rc0, GRT50 0 overflow) re-extracted with main trial_tap_arrivals --physical-paths
--node-cell-names (epyc2 die-qc-66-clk/ca/proofP). Ring = AS-BUILT: plan count_aligned_cycles + DEPTH from
results/qc_die57_1031/bind/sidecar.json (all 2525 depth 4, sched_lat == plan cycles on 2525/2525).
Interval = die_sta_related.sta_port_intervals (THE --count-align gate model; nominal, CPPR-LCA, inv2), lag
L = (cycles - 1) T + d (+-0.05 x unshared wander), guards L_lo - T/2 >= 100, (DEPTH - 0.5) T - L_hi >= 100 (ca_judge66.py).
Why not die_sta_related --count-align directly: the as-built sidecar bind has no plan L/d rows and no proof-timed START
ports (start_plan56 of DIE-QC-56/57 is gone), so the gate reports no taps 2525; the judge reproduces its port rows.
Result: 30 FAIL low side (TT worst -169.1, FF -18.4), all su_l0 slices (x_su_l0_ctl 12, x_su_l0_sc 12) + sl_E*_st_a x_st_a_fe__4 (6),
0 high-side; class = real cycle mismatch from the v2/v3 su_l0 early-merge clock form (not a missing bind).
+1 cycle on those 30 (3 -> 4, judge_v3_delta.json): 0 fail, TT lo +100.4 / hi +137.8, FF lo +154.2 / hi +321.6.
Not covered: START-tree skew/cleanliness on the v3 proof (as-built start ports not re-timed).
