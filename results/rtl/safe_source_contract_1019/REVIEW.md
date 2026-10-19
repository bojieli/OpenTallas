# Source-only SAFE contract prototype

ROOT authorized this standalone source prototype for opt-in NEW kits. It has no gate,
submit, daemon, HELPERS membership, or production integration. Existing checks and
legacy behavior are byte-identical. A `PASS` means the supplied mapped graph's
nonclock logical pin counts satisfy the bound; it is not a SAFE tile approval.

`tools/closure_loop/safe_source_contract.py` consumes flattened mapped Yosys
`write_json`, exact source identities, and one consistent native Liberty set.
The adjacent JSON schema requires `enabled=true`, `new_kit=true`, and
`production_activation=false`. All source/netlist/library digests are checked;
collector and reused Liberty parser digests accompany every result. Netlist and
library parsing use the exact verified byte snapshots, avoiding a later reread. Hashes prove
artifact identities, not source-to-netlist equivalence or complete source manifest
membership. Production use would require trusted synthesis receipt binding, owner
schema/source review, native physical correlation, and explicit activation.

The census recomputes every root; it never reads a reported maximum. It retains
uncapped endpoint identities and inversion parity for every mapped cell output,
top input, and static literal. Physical native tie outputs are ordinary counted
static drivers. Loaded Yosys literal bits are counted and force `HOLD` pending
explicit physicalization; they cannot disappear into a constant exemption.
Native pin directions must exactly match every mapped connection, with no unknown,
missing, extra, inout, undriven, or multiply driven logical pins.

Only a nonsequential single-input/single-output cell whose native truth function
is identity/inversion is transparent, independent of its master name. Traversal
preserves inversion and rejects cycles or ambiguous reconvergence. Two pins on one
sink count as two loads. Merged RTL copies are judged by the surviving mapped
connections. Every FF, combinational, top-input, macro, reset and static cone is
included, with endpoint classes retained. Native Liberty `clock=true` or FF
`clocked_on` roles separate clock endpoints individually. A net or master name
never grants a clock exemption; mixed clock/data roots retain their data/reset
counts. No timing or clock-spread waiver follows from this census.

Every input bit retains actual terminal roles and whether all its nonclock first
endpoints are FF data pins. Every output bit retains its unique logical driver
through BUF/INV and whether that driver is an FF. Shared output ownership remains
visible. First-combinational input cuts, reset landing depth, pin placement,
clock references and compiler ages require owner review; this tool does not mark
them qualified or waive them.

Existing collectors were reviewed before implementation: textbook_lint's native
classification and macro-direction fallback use names/inference and its usual
high-fanout path excludes constants; rst_port_fanout is reset-named and generic-FF
specific; landed_parent/check_safe_fanout checks selected local selectors only.
Those remain unchanged. The new adapter reuses tools/dft/liberty.py's group and
Boolean parser rather than a second Liberty expression evaluator. Unlike its
permissive cell merger, this adapter rejects duplicate masters/pins. Native bus,
bundle, latch, statetable and three-state constructs are intentionally unsupported
and fail closed; macro buses must not be silently approximated as scalar pins.
Physical PG-only pins are not logical loads and must be audited independently.

Validation: the committed fleet log records 15 adversarial tests, including
multilevel BUF/INV collapse, merged copies above 32, reset/top-input fanout, exact
pin-versus-cell counts, macro/tie/literal roles, fake BUF names, real clock-only
and mixed clock/data roles, shared FF output ownership, unknown directions/pins,
multiple drivers, transparent loops, rejected buses/duplicate libraries,
reported-maximum tampering, source digest mutation, and opt-in guards. Fixtures
exercise the mapped graph directly; no synthesis or place/route qualification is
claimed. No local heavy job or CTS build was run.

Before activation: review this schema/source; bind exact trusted synthesis inputs
and outputs; extend real macro bus support with native bit expansion and tests;
compare against at least one actual source-pinned native census; only then propose
an independently reviewed production guard change. This branch authorizes none
of those steps automatically.

Determinism and resources: roots/endpoints are sorted by their full identities.
Top-port indices denote mapped JSON bit-vector positions. Traversal is iterative
with explicit cycle tracking. No root/endpoint truncation or guessed size cap is
used; memory is O(input graph + complete emitted records), which can grow with
all per-root endpoint lists. Production-shape runs therefore need measured fleet
RAM admission. Unsupported compound FF clock expressions fail closed.
