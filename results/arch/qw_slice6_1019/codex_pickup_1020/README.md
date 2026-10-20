# Slice6 result pickup, 10-20

The current xhead-split cut at d1efba843 passes zero-offset extraction lockstep in all four modes (124,614 comparisons each), dv_bench2 f/j/k/q/m/n/o, and the landed parent versus its schedule-lagged reference. These are functional extraction checks, not physical closure or production-throughput qualification.

The older db6517ee8 landing mutants 1 and 2 fail as expected. Mutant 4 PASSES: reset-run perturbation remains unobserved, so it is not a valid fail witness. The older 886e32541 d10 and lane-offset mutants fail in random and legal modes. Source refs are deliberately retained separately; they do not establish witnesses on later changed RTL.

No new job, route, or submit was launched to collect these records. PRE-GATE native census blockers in multiple leaves must be fixed before accepting earlier WARN gates. The parent price is approximately 536 added cycles/layer (8.3%), above the accepted 327 (5%); coordinator decision or forwarded-pass implementation remains required.
