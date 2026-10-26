LEC remaining-cone runtime repair

ABC &cec -C limits conflicts at EACH INTERNAL NODE. Recursive CEC on engine cone7861
(lookup fault,135inputs/4799ANDs) spent over20min without a result. Naive single-output
SAT uses the declared conflict budget for the cone query:10k returns UNDECIDED in0.65s;
100k returns UNDECIDED in8.06s. The r8[2][17] cone9121 is SAT immediately (26inputs/107ANDs).
These are capacity/difference diagnostics, not a full engine equivalence PASS.

Leftover cone queries now use &cec -n -m; independent batches may run with --jobs N.
The default remains one worker. Callers admit matching threads/memory through ot-run.
There are no wall-time timeouts or proof waivers. Unknowns remain UNDECIDED.
The result parser preserves mixed trivial/UNSAT/SAT/UNDEC replies in output order;
a regression specifically guards against assigning a later proof to an earlier unknown.

Validation:12purePython tests PASS. Actual CLI csa31 controls with --jobs2 PASS:
pre keeps7differences y[24..30], fixed109/109 points proved (intel1 unit oth-ubuntu-1561829-1792924375).
The complete new engine snapshot proof is running at
intel1:/srv/opentallas-scratch2/claude/codex-lec-1025/engfix_naive_full,
ot-run16GB/8threads, unit oth-ubuntu-1560462-1792924363.
