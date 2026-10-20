# Final full cohort for exact reviewed source 38a7dca6b

The complete frozen source cohort finished with 112 failed, 1713 passed,
41 skipped, and 448 subtests passed in 277.36 seconds. All 17 added OOM ownership
controls pass. The complete FAILED/SUBFAILED multiset and all 728 error lines
match the retained committed efa baseline, with no added, removed, or changed
failures. This is regression parity with existing failures, not an all-green suite.

Source: 38a7dca6b1bc39f503fbfff1fb1e6171bc3e21b9. The three source/test files
match both the committed objects and the frozen fleet snapshot. No source changed
after the freeze. This final full run includes the independently reviewed kernel
companion incarnation lower bound. It supersedes the earlier focused-only limit
for that unchanged source; all earlier receipts remain preserved.

Baseline: results/rtl/pg_flow_review_1019/policy_final_full.log at
efae17de2128f3813aff8cf76226e8be8d60ea97.
The exact baseline SHA is in source_manifest.json. No baseline rerun or earlier
job restart was performed. The comparator normalizes file locations only and
preserves complete failure identities and exception details.

Fleet unit oth-ubuntu-2227362-1792448582 on ot-epyc8 was admitted via unpinned
ot-run with an 8 GB reservation and four threads. The exact pytest command,
source SHA values and final counts are recorded in source_manifest.json.

No main publication, runtime staging, service restart, active-attempt mutation,
cancellation, or retry was performed. The sole merger owns the one-file runtime
plan. ROOT exact approval and stop-before-publish remain required. PID-only,
generic-run and shared-cgroup OOM events without sufficient independent ownership
continue as visible UNKNOWN diagnostics; this run adds no physical qualification.
