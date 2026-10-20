# Stage OOM attribution correction

> Final full validation for unchanged source `38a7dca6b` is recorded in
> `final_reviewed_38/README.md` (from the parent packet directory).

> This packet records candidate `489ae20ee`. The subsequent kernel companion
> incarnation lower bound and its focused validation are recorded in
> `context_review/README.md`; the full-cohort results below apply to `489ae20ee`.

The daemon attributed the October 19 04:16:27 PT kill of PID 1022170 to
`bfh_compact199_col_pinreg_prepabs_1019` route.a1 at 14:34:36 PT. The
attempt actually began 04:11:38 PT, so the event was inside its time window.
The native systemd journal proves the killed process instead belonged to
`oth-ubuntu-1022074-1792408463.scope`, running the unrelated `idxrd_campaign.sh`
`dq12` campaign. That scope reported a `24G` memory peak and OOM termination.

Route.a1 ended at 14:33:49 PT with process return code 0. Its timeless sampled
PID union contains 1022170. This establishes misownership; exact PID reuse
cannot be proved from the old sampler's records. A return code of 0 establishes
process completion only, and does not establish physical qualification.
The daemon's automatic attempt2 remains untouched, as do both original attempts.

The corrected runner records PID birth ticks, boot ID in journald's 32 hex
format, derived birth time, observation time, and native cgroups. A kernel
`task_memcg` companion must agree with an already observed process incarnation
and a cgroup observed to contain only this stage's process group. Each kernel
companion is consumed once and cannot qualify later PID-only earlyoom messages.
Shared session/user cgroups cannot establish stage ownership.

An exact `RUN/cl/<stage-tag>.sh` path in the event is an independent ownership
witness. Generic RUN text is insufficient because bench and route siblings
share the run directory. Token boundaries distinguish route.a1 from route.a10,
backup suffixes, and paths under other directory prefixes. Bare PID membership
and an earlyoom service's own cgroup cannot prove target ownership.

All structured journal bytes and unsupported events are retained on the fleet.
The daemon logs the unknown-event count and exact `.oom_unattributed` and
`.oom_journal` paths without claiming an OOM retry. Genuine kills may remain
unattributed when native ownership evidence is insufficient. The sampler runs
every 15 seconds; short-lived processes may disappear before capture. Generic
shared cgroups, PID-only earlyoom text, missing native metadata, and unsupported
controller-specific cgroup mappings remain diagnostic. No arbitrary event-age
cutoff is used. Sampled cgroup membership is not lifecycle tracing.

Source base: efae17de2128f3813aff8cf76226e8be8d60ea97 (reviewed PG integration).
No main publication, runtime installation, restart, cancellation, or retry was
performed by this diagnostic lane. The helper is embedded in the shipped runner,
so it adds no separate mutable remote helper dependency.

Validation covers native /proc birth/cgroup/boot format, same-incarnation kernel
positive, pre-birth/first-observation/previous-boot refusals, actual dq12 scope
mismatch, shared scopes, exact stage earlyoom positive, sibling paths and suffix
refusals, consume-once kernel contexts, shipped-helper CLI output preservation,
and visible daemon diagnostics without an ownership claim. All 16 added controls passed in the exact frozen fleet cohort: 112 failed,
1712 passed, 41 skipped, 448 subtests passed in 277.12 seconds. The comparator
preserves the exact 112 FAILED/SUBFAILED records and all 728 error lines from
the committed baseline, with no added, removed, or changed failures. This is
regression parity with existing failures; it is not an all-green suite.

Baseline: `results/rtl/pg_flow_review_1019/policy_final_full.log` at the source
base above; its bytes and SHA are independently bound in `source_manifest.json`.
The three candidate source/test SHA values match the admitted fleet snapshot.
The run was unit `oth-ubuntu-2168204-1792447926` on ot-epyc8, admitted through
unpinned ot-run with an 8 GB reservation and four threads.

This changes operational failure attribution only. Physical acceptance predicates,
timing, and PG qualification remain unchanged. The neutral Gate-Rule records that
scope; the evidence threshold for an automatic OOM retry is stronger.
