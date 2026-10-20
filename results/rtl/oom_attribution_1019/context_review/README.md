# Kernel companion incarnation lower bound

> Final full validation for unchanged source `38a7dca6b` is recorded in
> `final_reviewed_38/README.md` (from the parent packet directory).

Independent merger review found that a kernel task_memcg companion could remain
unconsumed if its killed-process record was absent. A later reused PID with a
new sampled incarnation could then inherit the old cgroup claim.

The new control constructs exactly that case: companion timestamp 50, missing old
kill, new process birth 100/observation 150, later kill 200, matching cgroup text.
It fails against candidate 489ae20ee (before_fix_witness.log) and passes after the
fix. Cgroup ownership and mismatch evidence now require the companion timestamp
to be at least the sampled incarnation's birth time. An independently exact
stage-script witness remains separate. No arbitrary age threshold was added.

The final focused fleet run passed 17 tests in 0.67s, including all prior identity,
CLI and daemon-diagnostic controls. Unit oth-ubuntu-2225322-1792448409 was admitted
through unpinned ot-run with 2 GB/two threads. The 3 source/test SHA values exactly
match the fleet snapshot. This revision has NOT run another full suite, as
requested by the independent reviewer. Candidate 489's full 112F1712P/41skip/448
subtests and exact 112-case/728-error baseline comparison remain preserved as
prior evidence; those broad results are not attributed to this follow-up.

No runtime, service, active attempt, cancellation, retry or main change occurred.
ROOT review and solemerger integration remain required before operational use.
