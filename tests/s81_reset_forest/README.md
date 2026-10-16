# S81 reset forest candidate

This is an opt-in structural replacement mechanism, not a closed die reset network.
The existing immutable c26b_r/c26d2 sources are unchanged. Run `tests/s81_reset_forest/run.sh`.

`tools/s81/reset_forest.py` accepts source-bound, actual placed reset pin positions,
reserved legal hardleaf sites, per-domain compensated clocks, and measured pair
checks. It builds source-rooted forests, bounds every branch and terminal edge by
500 um and the actual TT pair budget, requires FF hold/recovery/removal >= 0, and
pads the terminal leaf to a uniform compiler-visible release calendar. Cross-domain
reset destinations require separate qualified roots. No clock or timing threshold
is relaxed. The supplied clock must run during initialization.

The CLI verifies SHA256 of the source manifest, full model file and actual
placement file, and matches **every** original reset/col_reset/reset_tree endpoint
before writing output. Pin IDs are arbitrary stable names; each pin also identifies
its original `instance` and `port`. Sites have distinct input/output pin IDs and
must be reserved from real nonoverlapping space, not instance-centre guesses.
`pair_checks` are keyed `driver_pin_id->load_pin_id`, and carry source and placement
hashes plus FF hold, recovery and removal slack. Missing records reject an edge.
Candidate output includes actual RTL, its hash, the real reset-leaf RTL hash, port
mapping, register count, area, all edge lengths/pair setup margins, and reset release
cycles/ps. A failed invocation does not produce a candidate.

The behavioral mechanism is `ot_s81_reset_leaf`: two local reset synchronizer flops
and DELAY_CYCLES additional reset pipeline flops. It asynchronously asserts and
synchronously deasserts. A delay=1 leaf releases on edge 3. A depth-D forest releases
all terminal leaves on edge 3D; shorter branches carry explicit extra leaf padding.
The calendar begins at a *qualified domain release*, not an asynchronous pad whose
synchronizer phase cannot be deterministic. No runtime credit, polling, backpressure
or production-data latency is added. Every hardleaf and clock entry still needs
actual physical implementation and reset recovery/removal signoff. Cold/warm
initialization cycles and any restarted program must be priced explicitly by the
compiler before integration; they are not hidden inside measured token timing.

The optional existing-generator flag `--col-reset-strict` requires
`--col-reset-tree > 0 --col-reset-span 250` (any positive span <=500 is accepted).
It processes small fanout column nets too, rejects missing clocks/unresolved sinks,
refuses the previous unconstrained `P.near(prev=None)` fallback, and rejects a branch
whose conservative full macro pin-box bound exceeds 500 um. This only rejects unsafe
placements; it does not claim pin-level timing, RDC qualification, or repair the raw
stream/serial reset nets. Use the forest planner for the replacement architecture.

Actual c26b_r audit established rst_stream has 813 terminals and a 33,724.742 um
first-endpoint branch (589 missing exact anchors), while rst_serial has 36 terminals
and an 8,218 um branch. Thus no full current-die forest can honestly pass yet: the
pin exports, legal hardleaf sites, exact clock assignments and pair/RDC measurements
must come from the die lead. The model endpoint inventory is authoritative; the
planner's unit fixture is only the smallest complete mechanism test.
