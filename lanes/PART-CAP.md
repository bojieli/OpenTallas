# PART-CAP (branch claude/part-cap-1024, worktree ~/wt/part-cap)
Goal: origin of the 400k cells/partition cap; measure ORFS/OpenROAD scaling ASAP7 833 ps at ~0.4/0.8/1.6/3M cells;
recommend max partition size. Measurement only (no die-plan edits). Results -> results/arch/part_capacity_1024/.

Step: (1) origin search in progress; (2) building replicated-tile vehicle (N x closed ot_qkh_lane8, ~114k cells each).
Origin so far: CORE_CELLS_MAX=400_000 added by c6376fe8a8 (COORD 10-23 19:36 "CORE-KS"); first appears in KV plan v3
(9292db97f4, 10-23 06:32) "CAP MEASURED 06:1x: 400k std cells per OpenROAD run, 500k ceiling" -- the measurement itself is
not committed (coordinator notes lost with rtx-pro).
Runs: (none yet)
