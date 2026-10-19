# Source-only SAFE contract prototype

ROOT authorized this standalone source/schema prototype for opt-in NEW kits.
There is no gate, submit, daemon, HELPERS membership, or production integration.
Existing checks and legacy behavior are unchanged. No main merge or production
activation is authorized by this packet.

`tools/closure_loop/safe_source_contract.py` consumes flattened mapped Yosys
`write_json`, exact source identities, and a consistent native Liberty set. The
adjacent JSON schema requires enabled=true, new_kit=true, production_activation=false.
Source/netlist/library digests are checked; netlist and library parsing use the
exact verified byte snapshots. Collector/parser digests accompany CLI results.
Hashes identify supplied artifacts, not source-to-netlist equivalence or complete
source-manifest membership. A trusted synthesis receipt remains an activation
prerequisite. Pure API diagnostic replay does not forge a NEW-kit flag for old kits.

The census recomputes every root and retains uncapped endpoint identities and
inversion parity for every mapped output, top input and virtual literal. Two pins
on one sink count as two loads. Only a function-proven nonsequential unary BUF/INV
is transparent, independent of its name. Cycles and ambiguous graphs refuse.
All FF, comb, input, reset, macro and native static tie roots are included.
Only actual native Liberty clock=true or unary FF clocked_on roles separate clock
endpoints individually. Mixed clock/data roots retain nonclock counts; names or
whole clock nets never grant exemptions. No clock/timing waiver follows.

ROOT confirmed virtual 0/1 literals force overall HOLD until actual physical tie
implementation and load/cost proof, including when their inventories exceed 32.
Those exact counts remain visible as literal_load_excess. Ordinary roots or real
native tie-cell outputs above 32 FAIL. X/Z/undefined bits refuse; they are never
physicalized as a chosen constant. No SOURCE PASS follows from an ordinary-only
predicate under HOLD.

Every input retains its actual terminal roles and whether its first nonclock
endpoints are exclusively FF data pins. Every output retains its unique logical
driver and whether that driver is an FF. Shared output ownership remains visible.
Reset landing depth, stopped-clock behavior, source functional lifetimes, actual
pin placement and compiler ages remain separate owner/source obligations.

ROOT explicitly approved disconnected OUTPUT records: exact cell/pin/direction,
net=null, zero downstream logical endpoints. Open BUF/INV outputs retain actual
INPUT pin/net/native capacitance attributes and units; zero physical load is never
inferred. Open inputs, empty top ports and undriven top outputs refuse. No
functional net, tie, or stub is fabricated for clock-capacitance BUF instances.

The strict native adapter reuses tools/dft/liberty.py's group/Boolean parser. It
selects the instantiated logical masters from the actual mapped graph; unused
library models are ignored while complete original files remain hashed. Unknown
or duplicate used masters/pins, direction mismatches, missing/extra connections,
inout logical pins, buses/bundles/latches/statetables/three-state constructs and
compound FF clock expressions fail closed. Unsupported used models require a
reviewed extension. All graph references must resolve in the selected libraries.

Previously audited collectors remain unchanged: textbook_lint uses name/inferred
native classifications and normally excludes constants; rst_port_fanout handles
reset-named generic cones; landed_parent/check_safe_fanout targets selected local
selectors. Their reported maxima are never inputs to this prototype.

Final exact collector SHA:
893a3f5566752a5ee38b7dd3495b43d8d84258cbbd49b975b3e01a38707bb9dd.
The final unpinned fleet unit oth-ubuntu-1936060-1792439820 on ot-agidock128 RAN
exit0: 19 adversarial tests PASS, then both real diagnostic expectations below
confirmed. See final-tests-native-source.log. Tests include multilevel polarity,
merged copies, exact pin counts, reset/input/macro/tie roles, fake BUF/clock names,
mixed actual clock/data pins, open clock and nonclock BUF outputs, native unused
versus used unsupported models, unknown/multidriver/undriven/X cases, literal HOLD
versus physical tie FAIL, ownership, tampered maxima and opt-in/hash guards.

The actual INT8 native negative uses original OpenDB
SHA3e3d3df1b4247ba46b8c6d0388e84fdda89675351d314cb8165eb7329d923f19,
independent faithful raw JSON
SHA7ae2cc0705d6369853e46ce46218ab26c92f2d6f9ae7bff334b5e03ee5bba54b,
and the exact five real RVT TT libraries. It independently finds FAIL/max 110:
17 canonical FF roots (16 pend 85..110 and reset 87), plus 37 transparent-output
records carrying the same excess, yielding 54 all-driver violations. Full output:
final-native-census.json.gz and final-native-summary.json. All 3025 PG-only cells
are retained in provenance with actual complete native master supply MTerm roles;
30,934 instance supply pins and two top supply pins are omitted from the logical
graph by role, never by master name. Three unused copied FAKE libraries remain
hashed but unparsed; every used logical master resolves in the real native set.

The actual source-only successor da40a2a46 mapped graph
SHA8e4fdb42a22d755e7efb9cfcdf1ac0efe1563ee500d177e2d8e810fd15b85d27
independently yields overall HOLD: ordinary max 24/no ordinary violation, virtual
constant loads 0=64/1=202. All data inputs terminate first at FFs and outputs are
FF-owned. This is a partial source predicate; physicalization, native physical
checks and complete SAFE qualification remain open. See final-source-census.json.gz,
final-source-summary.json and replay_source_int8.py. No synthesis/CTS/place/route
was launched by this task.

Original raw inputs and library SHA manifest remain at
/home/ubuntu/artifacts/hbm-int8-raw-export-1019/t1 and agidock128's corresponding
/srv/opentallas-scratch/claude/hbm-int8-raw-export-1019/t1 directory. Final reports
remain under agidock128:/srv/opentallas-scratch/claude/safe-source-contract-native-1019.
All initial strict refusal/comparison-assertion witnesses are preserved in this
packet. Old 15/18-test source snapshots remain identifiable in their exact logs.

Roots/endpoints are deterministically sorted; top-port indices denote mapped JSON
bit-vector positions. Traversal is iterative with explicit cycle tracking. No
arbitrary root/endpoint cap or truncation is used; memory scales with input graph
and complete output records, so production-size replay needs measured fleet RAM
admission. Native replay used 8 GB admission and took roughly 4 seconds. Physical PG,
capacitance/timing, placement, clock boundaries and behavioral qualification are
not replaced by these logical counts. ROOT source/schema review and trusted
synthesis binding remain prerequisites to any separately authorized activation.
