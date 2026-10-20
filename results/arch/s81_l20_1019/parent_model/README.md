# L20 reader-row parent model: blocked, no physical grant

The 16 abutting readers remain a model direction. This packet corrects the raw
reader-row arithmetic against MU3's actual eight LK rev2 slots and preserves the
source tests. It grants no parent outline, fit, rate, native timing or token claim.
Source is `2b7827041`; MU3 reference is `293b25c2f`. The two input plans and every
source hash are recorded by `recompose.py` in `model.json`.

ROM capacity is 1130 to 1070 slots: loss 5.3097%, ideal fully occupied capacity die
increase 5.6075%. Actual production per-stage ROM payload and rank reassignment
are missing, so the production die count is **null**. Multiplying a fractional
9.7 dies/layer by a global ratio cannot replace that manifest. Conditional bounds
are explicit: 520 fully filled interchangeable old dies require at least 550 new
dies globally, or 552 when all groups must contain a multiple of four. A fully
occupied old 10-die layer copy needs 11 new dies, making eight such duplicated
copies 88 rather than 80 dies. These are sensitivities, not a selected design.
Existing SU topology is TP4 times six dies/rank =24 participating L20 rank dies;
MU's old 10 owner plus10 shared helper dies and copy-A/B calendar are not a new
capacity or physical qualification.

The 518.4 by777.6 reader proposal occupies403107.84um². The quoted196973um²
standard cells are48.86% of the whole outline, but54.63% after six real native
SRAMs are excluded. Channels, PG, clock, halo and detailed legal placement remain
unpriced. Its current source kit remains1058.4 by1101.6. More decisively, the actual
172.8 by41.04 native256x256 SRAM LEF exposes411 west and410 east non-PG contacts:
10.015/9.990 contacts per full-face um, exceeding the6/um rule. A truthful wider
pin-family model with electrical cost is required before approving this reader or
a TX using this family. No macro pin escape is inferred from area fit.

The raw plan's eight SerDes slots were260 by2250. Actual MU3 LK rev2 slots are
259.2 by3596.4, adding2.77749504mm² total. Their actual locations are in
`model.json`; the reader-row cut0.5663/396572bit-mm/846540relay-bit-stages cannot
be advertised as current after swapping the slots. Full current link retargeting,
overlap, channels and PG are unproved. The proposed SVC reserve1252 by1235 has
1.546220mm²; its1.037fit uses the historical1.491mm² estimate. Actual SVC native
area and fit are null.

The raw plan does include17/17/33 intermediate stations on the long query/query/
score-tail paths. Maximum analytic polyline segments are402.8/404.6/398.7um;
the second query has only0.4um reserve. These are box endpoints, not registered
native pin endpoints. The exact station point lists and endpoint identities are
retained. Native face offsets, register ownership, forwarded phase, landed reset,
clock insertion and compiler latency still require proof. The source section's
513-bit QF links also need a production binding to the plan's two276-bit lanes;
neither a width total nor section binder PASS proves that serialization.

IDX egress contains positions without scores. Scores must be retained and
re-encoded at the sending TX. Source implements8192 times256bits =2097152 score
bits, plus64 times512 useful IDX buffer bits. `SRAM_MACRO=1` uses32 score and2
IDX256x256 macros (2228224 physical bits). If bound to the current reader native
family, raw macro area alone would be241118.208um² per TX; exact physical binding,
clock/PG, mux fanout and parent slot remain null. The die section opts into SRAM;
the existing k3/k6 composed TX bench does **not**: it uses default behavioral
`SRAM_MACRO=0`. Thus its numerical PASS is not a native SRAM contract PASS.

Exact arithmetic over all four ranks and every transmitting k3/k6 subtree shows
the absolute window index modulo8192 is injective within each job's subtree.
The largest transmitting L20 subtree is[131073,262144):131071keys and8192 windows;
the source comment's131073keys is inaccurate. This result does not prove lifetime.
The memory has no reset, capture is always on, writes are per-score masked, and
same-edge read/write returns OLD. A production replay must show each selected
score lane was written in the current generation before read, no cross-job alias
while previous reads remain live, two-edge macro/bank-select latency, disabled
read hold, and arbitrary stale memory/reset/restart correctness. These predicates
remain null, alongside residual indexed queue safety.

`production_trace_contract.json` preserves exact compiler summaries, stimulus and
expected-output hashes for the existing k3/k6 static plans. At t_q200 the k6 root
last egress is18116 (17916 relative), and k3 is22607 (22407 relative). Each child
reserves1600 slots at pitch1; the five k6 tree edges reserve2208000 bit-cycles per
rank on276-bit links, excluding query and all other traffic. This is reserved
bandwidth, not switching activity. The compiled leg remains729 edges and is not
validated against the new native station/serialization implementation. Actual
crossing energy and SU token/MU period are null; energy needs real transferred
bits, calibrated energy/bit, register/relay and clock costs.

Existing exact-source evidence is retained: k3/k6 TREE_RD PASS; corruption and
three TX mutants FAIL; reader open-lane positives PASS and omitted-mask MUT6
FAIL. The corrected QF bench was independently rerun on fleet Verilator5.050:
positive nerr0 PASS, next-UID mutant nerr67 FAIL. Source RTL stayed byte-identical;
only the previously corrected valid-qualified checker is used. Historical QF
positive failure is retained separately. No arithmetic rebuild, full die build,
gate, route or submission was launched.

Reproduce the bounded arithmetic with `python3 .../parent_model/recompose.py`.
Next required packet: actual ROM payload/rank/die manifest; current complete MU3
geometry with LK rev2; truthful native SRAM family; exact producer-to-TX SRAM
generation lifetime; QF lane encoding; and compiler-bound native landed hop/clock
latencies. Only after that packet can parent sizing and a physical vehicle be
reviewed.
