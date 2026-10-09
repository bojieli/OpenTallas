Routine tokpipe verdict reentry correction.
The original check had no SS acceptance term. Its full TT/FF custom check blocked hold_only before the normal FF ECO; original metrics and failed state are retained.
This additive helper separates TT/DRC independent eligibility from mandatory FF closure. All four modes (incontext, reg2reg, region, die150) remain in the metrics and final custom check. It emits an exact constraint union for generic ECO use, starting from the original byte-identical833ps signoff,60/25 and retained150/90 regional terms.
No RTL, released payload, benches, clock target or uncertainty changes. Existing source9f remains pinned; new helper and SDCs are an explicit source overlay. Source overlay must be present before spec commands change.
The final custom check is conditional on current-ODB/SPEF/SDC hashes and all original mode constraints recomputed by existing WFC STA after ECO install. Original STA/DRV are copied to .pre_eco before regeneration.
E1 measured-admission observer must prove original TT127.4/FF-8.2 equivalence before frozen state is reentered. No generic770 ECO is allowed.

Actual loop custom metrics_cmd drops ECO metadata. Corrected spec therefore uses NORMAL corner_sta plus actual drc_metrics parser, not metrics_cmd. The normalized equivalent observer JSON retains private oracle provenance while binding orfs_dir to original immutable route. Parser output must contain exact post_sdc scope before reentry.
