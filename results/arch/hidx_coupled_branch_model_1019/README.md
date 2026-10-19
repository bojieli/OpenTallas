# HIDX coupled branch SOURCE model — live first construction

This is a default-off, pure analytical source model. No synthesis, placement,
OpenROAD, router, CTS, RTL change or production adoption occurs. The exact
11,145 native cells, 2,904 FF, 140.4 um outline, existing fixed ports, source
cycles and every 80 fF external output load are unchanged. No buffer was added.
Actual checkpoint 70042afe82ff76fc2657f45fb6c2a89f91eed2993add8e9dc89f2fc612fc88a6
and the failures in b3368458e / 148b / 3163 remain immutable.

The constructor grows each net through nearest native contacts or projections
onto an existing same-net segment. Each selected branch jointly tests both
vertical columns, the full horizontal interval and both contact jogs before
committing any ownership. Same-net overlapping segments are unioned for wire
capacitance. Each fixed contact pair exhausts the finite PG-clear H/V domain,
with length lower-bound pruning. The selected topology and inter-net ordering
are deterministic heuristics; failure is not a global infeasibility proof.

The unchanged candidate domain contains 2,140 M2/M4 H rays, after 128 candidate
clock ray reservations, and 5,202 M3/M5 V columns. The first implementation has
a worst-case 57,910,120,560 column-pair candidates per selected branch. The
actual unpinned fleet run was admitted on ep7 as unit
oth-ubuntu-286529-1792451856, native Python PID 286560, client session 77182,
16 GB / 2 threads. Remote directory:
/srv/opentallas-scratch/claude/hidx-coupled-branch-model-1019.
All four inputs and source passed the pre-run hash check. The latest observed
completed 100-net checkpoint is ordinal 3,400: 3,401 nets / 6,550 native contacts
have modeled branch connectivity, with zero wire-cap excess in that prefix.
These are partial counters, not a completed census or PASS. The running source
has no inner candidate counter, so its exact current branch is unavailable
without intrusive inspection. Preserve the run; do not restart or modify it.

The separate interval_successor.py is an UNEXECUTED optimization kernel, not a
second construction. For each H ray its forbidden ownership intervals partition
columns into free connected components. Endpoint V/jog feasibility is separable.
Prefix minima of |bx-w|-w and suffix minima of |bx-w|+w find the exact same
column-pair minimum in each component, with original A-rank/B-rank tiebreaks.
The outer H-ray order and strict improvement rule must remain unchanged when
integrated. 4,032 small exhaustive adversarial candidate/cost/tie comparisons
pass, including empty domains, duplicate layer columns, touching and overlapping
blockers and equal-cost choices. This is an algorithmic equality check only.
No successor heavy run or old-job termination is authorized by this receipt.

All 31,384 native contacts must receive final connected or failure witnesses.
Incomplete nets must have null complete root-path evidence. Root paths reported
by the constructor are explicit valid tree-walk lengths, not globally shortest
electrical paths. Shared segment joins may need native layer stacks. Local M1
access, local-jog PG clearance, exact default via CUT union/enclosures, signal
DRC, via fringe, all waveform/setup/hold, real clock phases, upstream fixed point
and fresh PG contact/conductor/short proof remain HOLD. A modeled branch graph
is insufficient for physical contact completion. Any weak-drive remedy needs
a separately priced native-function/cap/area/PG/upstream proposal before changes
to the old graph.

Inputs are byte-pinned copies from the preserved b336 demand packet under
/home/ubuntu/artifacts/hidx-joint-source-model-1019; INPUT_SHA256SUMS binds them.
The finite construction writes output/SUMMARY.json and output/branches.json.gz.
The separately prepared render.py is read-only and has not been run.
