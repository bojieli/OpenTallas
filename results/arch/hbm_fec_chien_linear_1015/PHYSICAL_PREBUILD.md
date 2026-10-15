# FEC physical prebuild: bounded steering is proven; physical closure remains open

Scope is the exact standalone full wrapper counted by `full_census/receipt.json`.
The joined endpoint, 613/487 gearbox, production calendar and delivered clock
family remain outside this receipt. No physical area or routed closure is claimed.

## Actual prebuild evidence

The admitted full generic-netlist analysis (`generic_prebuild.json`) sees 149,972
combinational cells. Its conservative scalar-expansion sizing model assigns
15.65 million units, principally to 114 shifts and 57 variable read selectors
(12.08 million units). These are deliberately conservative sizing units, not
mapped gates or area. Generic whole-cell connectivity also couples independent
bits conservatively; exact cross-root pin counts await the scalar graph.

One source-bound bit-mapping attempt was run from the already completed full
census netlist. At 03:34:30 PDT, the kernel killed Yosys in its 64 GiB cgroup with
66,967,380 KiB anonymous RSS. The tool returned 143 when its scope terminated.
`physical_prebuild/bit_mapper_0` preserves the input binding, map script, last
Yosys log and authoritative kernel OOM report. No scalar netlist was completed.
There was no larger-memory retry of that source.

The offending source structure includes 55 sequential variable-position
read/modify/writes of a 5,440-bit word, each correcting a 10-bit symbol. A safe
physical candidate must expose bounded, local symbol wiring rather than assume
these operations fit an old SerDes gap.

## Distinct structural successor

`gen_fec_static_correction.py` generates an actual combinational correction bank.
Existing 55 Forney values and hit bits enter fixed, symbol-owned 10-bit slices.
The existing cc=0..9 phase selects the slice group, with only 49 valid symbols in
phase 9. A balanced exact popcount counts the same valid hits. It adds no state,
clock input or cycle. Original and first linear-candidate sources remain intact.

Direct numerical proof exercises 16,144 vectors: every cc=0..15 value, error-value
basis, hit basis, all codeword input basis bits and random vectors, compared with
the original dynamic-write semantics. It passes; an actual steering-wire mutant
fails at phase 0/vector 0. Full actual FEC passes 2,048 words with unchanged age
102 and 2,376 decoded words checked; actual Forney MUT2 fails at cycle 302.
Proof logs are under `static_correction_proof/`.

The new full census completed with status 0, unit `oth-ubuntu-1799123-1792060811`.
It proves identical 86,152 FF bits and all 12 exact per-root counts, maximum 13,790.
Generic synthesis/check uses 451.66 seconds and 3,727.70 MB peak versus 683.82 seconds
and 5,229.71 MB before. `static_correction_census/` preserves exact source/receipt
and losslessly compressed log. The new generic model reduces conservative scalar
expansion 15.648M→2.405M units (84.6%), shifts 114→4 and shiftx 57→2.
The distinct static-source bit mapper completed; exact scalar counts and paths
are recorded in the completed-expansion section below.

## Placement and partition alternatives to measure

1. **Twelve root regions:** retain the current root-owned state as twelve hard
   leaves, allowing no leaf to inherit physical closure from the source count.
   Place capture -> syndrome -> four BM units -> Chien -> emit/CDC according to
   actual registered connections, with the TX collect/encode/codeword chain
   beside its own PMA pins. This is the simple comparison, not a demonstrated fit.
2. **Symbol-owned receive banks:** distribute the 5,440-bit current/original
   codeword registers into ten phase banks, nine of 55 symbols and one of 49.
   Match the emit capture banks to these banks, and place the four BM codeword
   stores beside the corresponding Chien bank faces. Keep the real BM polynomial
   arithmetic beside syndrome/coefficient interfaces. The new static correction
   steering enables this topology without adding an arithmetic edge. Actual
   cross-leaf buses, pin faces, area, clock delivery and legal geometry still
   need explicit RTL/physical interfaces before it is a hard-leaf inventory.

Both alternatives preserve current arithmetic, reset semantics and cycles.
Shared combinational logic must have an explicit owner or priced replication.
The exact scalar graph tool reports state-to-state logic levels, registered
source-bit crossings, external interfaces and shared/unique sink-root cones;
it refuses a combinational cycle or residual non-scalar primitive. Its method
is checked on a twelve-root graph with exact cross-root and two-level paths.
A successful source-bound scalar map is required before applying it here.

No route is authorized by this document. Next gates are: successful new-source
full census; bounded scalar expansion; exact state/clock and interface graph;
explicit hard-leaf source partition; actual TT library area and timing; geometric
pin/channel fit; then pre-route admission. Wire delay, reset delivery, recovered
clock phase, and joined endpoint roots remain separate mandatory checks.


## Actual current 512-pin system scope

The historical standalone mechanism above uses 544-bit PMA and 102-cycle age.
The current actual source is `ot_hbm_core_fec_frame_static_correction_link`,
helper commit 96c91fc64 with source-pinned receipts f72e2454d. Its actual 512-bit
PMA, core 1.2 GHz / FEC 16:17 families and 151-FEC-edge calendar pass 234 payloads / 66 idle slots,
2,048 decoded / internal CDC words, all four runtime mutants, and actual ForneyMUT2.
It has 23 named clock inputs (core + 16 FEC + 6 PHY); native TX6/RX2 endpoints remain
caller-owned. No standalone count transfers to that larger hierarchy.

Geometry/H-DIE owners confirm no current authoritative FEC slot or face/track
capacity grant. Their 68-node v15 contract has zero HOST/SerDes/FEC instances.
Historical 864 um E-strip and old HOST/HS slabs cannot constrain or price the new
actual hierarchy. `physical_prebuild/geometry_boundary.json` records this gap.


## Completed scalar expansion and critical-path bound

The distinct static-source bit mapper completed in 200.25 seconds, with
6,466.73 MB peak memory. `static_correction_bit_mapper/` preserves the exact
source binding, receipt, script and compressed log. The cached remote scalar
netlist has 1,113,044 cells: 85,638 FF bits and 1,027,397 combinational gates
(excluding nine scope records). The bit optimizer removes 514 redundant FF bits:
512 from collect and one each from control and emit; no state was added.

The actual scalar graph has maximum D-path lengths of 90 generic gates for each
BM unit, 87 for Chien/emit, 58 for capture and 49 for collect. These are exact
structural depth bounds, not sensitizable-path proofs or library delays. Maximum
registered-Q fanout reaches 6,929 in control, 5,903 in Chien and 2,887 in emit.
290,825 combinational cells feed more than one sink clock root. Candidate root
boundaries and registered source-bit counts are recorded in
`physical_prebuild/candidate_registered_boundary_inventory.json`; this explicitly
is not yet implemented hard-leaf source or a pin/clock/route grant.

The final-slice correction cone feeds both Chien and emit. A promising banked
partition keeps corresponding Chien and emit bit slices together while retaining
two distinct clock ports per leaf. This keeps shared correction wiring local,
while preserving both measured clock delivery obligations. Isolating the roots
blindly would require large combinational seams or priced logic replication.
Actual BM physical connectivity also includes 300 source-Q bits from every other
BM unit; the global syndrome array with a dynamic index is a structural scope
issue worth eliminating with unit-local storage. It is not assumed away as a
false path in the physical model.

An actual ASAP7 RVT TT library map is now running from the cached scalar graph,
without retiming. Its clock target is the actual current FEC period (conservative
885 ps ABC target for 885.416 ps). Area and delay remain unproven until collected.
A first tooling attempt was stopped after a small one-FF probe demonstrated that
missing imported liberty cell declarations would produce a false undriven-net
check. The corrected flow imports all five real RVT TT libraries and caches the
mapped JSON before final checks. This was a flow correction; no source hardware
or timing requirement changed.


## Measured current 23-root join

The exact current PHY512/core487/stepped613 hierarchy completed the admitted full
generic census with **177,666 FF bits across 23 distinct clock inputs**. Maximum
is **13,790**; every root is below the 15,000 source-count limit. The core root
owns 12,287 bits, FEC control 12,152, capture 8,219, and all eight physical gearbox
storage-bank roots own 8,704 each. Full Yosys synthesis/check used 475.53 seconds
and 5,349.46 MB peak. Unit `oth-ubuntu-1976184-1792062281` completed with exit 0.

`joined23_census/` preserves the exact source, script, receipt and compressed
log. `reviewed_summary.json` distinguishes the terminal measured result from the
raw receipt's retained input-manifest prepared-only wording. Caller TX6/RX2
endpoint state and SRAM remain excluded. No standalone area, timing or clock
phase is inherited. Geometry/H-DIE and the numeric join owner have the measured
current root inventory; no qualified current slot or track-capacity grant exists.


## Actual joined scalar graph completed

`joined23_bit_mapper/` binds the successful full-current scalar map and graph to
the measured 23-root source receipt. The mapper completes in 480.95 seconds,
12,384.73 MB peak, with strict netlist check PASS. It retains 176,662 FF bits and
1,543,463 combinational gates. Relative to the generic census, bit optimization
removes 1,004 redundant FF bits: core 488, FEC control 3, collect 512, emit 1.
No root is absent. The 1.135 GB source-bound scalar JSON remains cached remotely.

The full joined graph confirms maximum structural depths of 90 for each BM,
87 for Chien/emit, 58 for receive capture, 47 for each serializer bank and 34 for
each deserializer bank. Each of eight gearbox banks retains 8,704 FF bits.
Capture control reaches 9,223 registered-Q fanout; TX PHY control reaches 8,708.
These are real scalar dependencies and gate levels, not mapped delay or physical
pins. Every receive-capture root structurally sees all four deserializer banks,
and each TX PHY root sees all four serializer banks. Bank selection and control
must therefore be included in the physical home, not priced as isolated storage.

373,573 gates feed multiple sink roots. Summing independent per-root cones gives
2,213,570 gates, a 43.4% increase over the actual shared implementation. The
proposed matching Chien/emit storage banks preserve two actual clock obligations
and avoid blindly duplicating their shared correction cone. No hard-leaf source
partition or physical placement is implemented by this graph report.

The separate actual RVT TT mapper remains in ABC, with its authoritative child
process live at 100% CPU. Its original source/graph hashes remain unchanged.
A source-bound OpenSTA characterization runner is prepared and its real-library
one-FF tool probe passes. That probe validates the tool script only; it is not a
FEC timing result. Planned full characterization uses the actual 885.4167 ps
period with explicit ideal-wire/common-phase assumptions, no CTS/SPEF, no
qualified external driver/load, and no reset recovery/removal signoff. Geometry
outline, real face pins, track capacity, delivered phases, mapped total area and
whole-joined physical qualification all remain open.

The real RVT TT library area units are independently checked against the pinned
PDK's actual 1x LEF: all 202 cells have a matching macro and equal width × height.
`physical_prebuild/area_lef_check.json` binds image, five libraries, actual LEF
and checker hashes. A library area unit is therefore one µm² of cell footprint
for this kit. This establishes units for the eventual mapped total; it does not
price placement whitespace, clock tree, buffering or routing. The fail-closed
post-map audit also requires every clock root's FF count to match the cached
scalar source exactly. Five tests cover area parsing, residual generic gates,
unknown clocks, changed state inventory and incorrect LEF scaling.
