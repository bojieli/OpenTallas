# QC R29 FT geometry delta
Base18c6286d88387ac812ac0a74920fa8c4f275e1b5. Changes only FT-site fields
in7main-plan types; does not adopt separate native100 logical type set.
Apply with python3 results/qc_r29_planfix_1351/apply_delta.py INPUT --out OUTPUT.
Helper rejects changed original slot contracts. All stage counts are preserved;
ports/lanes/latency tables unchanged. Finalclock/reservation composition remains
master-planowner task.

apply_hard.py/apply_soft.py reproduce base allocations; combine.py emitsdelta
and audits all explicit banks. check_render.py fullchecks/renders; g0_only.py
rechecks corrected sparsecontext. See geom_review/qc_r29_planfix_1351/REVIEW.md.

Initial soft-knee failed aligned individualbit collapsedvertex IndexError;
0abf5b37b2 fixes topology with actualregression. Shared-knee successor proposed
1034FF/+2cycles; selected distributed waypoints remove both. First Wcws3 plan
added517FF/+1cycle; selected explicitcollar retains4stages. Exploratoryoutputs
preserved scratch, not adopted.

Scratch intel2:/srv/opentallas-scratch2/claude/codex-qc-event-1351-1027.
Selected hard2/plan.json +soft3/plan.json, combined/ audits/checks.
No P&R/STA job launched.
