# Qwen forwarded corridor and phase diagnostics, 2026-10-19

The original `forward1` diagnostic failed after all765 regional roots:
`no clock route (1940,854) -> (1691,877)`. Its complete failure log is
`physical/build_tt.log`. It produced neither a clock ODB nor a timing verdict.
Source is `codex/qwen-dieclk2-recovery-1019@42d93c5d8`, using GEN
`1075e50e2dcc1c25d15ab8232757bac665f11a1a` (dv2f16), not the live dv2f18dh2 GEN.

The actual adjacent hard blocks span y5529.600..10756.776um:
`c16_E0_1` x16951.680..19396.776 and `c16_E1_1`
x19414.080..21859.176. Their17.304um corridor contains12.960x6.480um
reset repeater blocks at10.800um ypitch. The10um conservative grid hides the
4.320um physical bays. No macro relocation or reach relaxation is justified.

`physical/corridor_occupied_geometry.json` replays the exact failed pair with
all hard rectangles and18333 placed standard cells. Actual ODB confirms
BUFx24=1.620x0.270um and BUFx12f=.972x.270um. Whole-footprint exact bays restore
26637 coarse cells; a670-step route has station bounds at most404.540um.
This proves the corridor representation change; the full new spine remains
unqualified until replayed after all765 new region trees have been placed.

The opt-in `spine.exact_footprint_bays` source fix takes that post-region ODB
occupancy, reserves every whole footprint, and checks routed length using
actual placed library pin coordinates. It keeps strict380um blocked runs,
405um stage reach and fanout2. `--geometry-only` writes a geometry manifest
before STA; it never produces a timing/admission claim. The recorded script
and exact spec replay the entire required spine before any new timing build.
Ten focused fleet tests pass. `reach_mutant.log` is the required independent
410um rejection witness; occupied bays, newly placed region trees and partial
footprint overlaps are tested.

Immutable inputs are on epyc4:
`/srv/opentallas-scratch/claude/codex-qwen-dieclk2-1019`.
Floorplan ODB SHA256:
`793ab8aedba4e0f7c8a0706ece9a776ff00c7ca09e9e7b3df175762ee563e53c`.
Hard rectangles SHA256:
`efeda305ec8b150318215cfe0197f23f68f1ae43586f24157f46e9406fdd3f81`.
Occupancy JSON SHA256:
`e5a6e1aa0a4b8d31726d2a87db17df38103a0bba41ef98cf57bbcd16a2bad810`.
Own replay/collector outputs:
`/srv/opentallas-scratch/claude/qwen-clock-phase-1019/baseline_measure`.

`qwen_qphase.py` binds actual GEN endpoint/relay/native clock pins and collects
single-corner TT/FF/SS raw pin arrivals. The old completed DME ODB was used only
as a collector runtime control, not as the failed forward1 candidate. Its
receipt remains BLOCKED: GEN mismatch, missing SAFE2 clock ports, assumed native
references, and unresolved propagated pin-clock tags. No prefetch advance or
production phase is admitted. Production still owes a source-bound programme,
512 Q writes/all32 requests and an actual per-endpoint phase replay.

The initial unresolved-tag receipt is retained. The subsequent collector uses
the clock-family owner's validated native `get_property $pin clocks`, followed
by `get_full_name`, and requires exactly one owner. The actual TT runtime control
in `physical/native_tag_control_tt` records those names and hash-bound arrivals;
its clocks are propagated and the timing search precedes property extraction.
The completed TT/FF/SS controls are joined in
`physical/native_tag_controls/baseline_native_tag_receipt.json`: each corner has
59 finite pin arrivals and59 unique named clock owners. The36 remaining blockers
are retained. This fixes tag collection without removing production blockers.

An additional physical-site audit found that all20 failed-pair witness stations
lack a containing physical placement row in the source ODB. Its1855 fragmented
rows are not a global site grid. Free hard-macro rectangles and a legal lattice
are insufficient to prove physical row legality. The final whole-spine ODB audit
must check actual row containment as well as overlaps, endpoint coverage, fanout
and405um reach. No timing proposal is authorized from the single-pair witness.

The independent auditor was validated on the completed historical DME ODB,
not the new candidate. `physical/legacy_geometry_audit/proof.json` records
109480 clock cells,36819 spine cells, zero bounding-box overlaps, but36766
spine cells and109395 total clock cells lacking physical rows. It also finds
865 inherited regional connections with direct distance>405um, the worst
`dc_r343_L1/Y -> rstt_rst_field_2495/clk` at2472.043um. The legacy control fails
the new proof as expected. These native regional and row/rail obligations
remain separate from the new spine's routed stage proof.

`qwen_spine_geometry_proof.py` independently reads the final actual ODB and
checks full footprints, actual net connectivity, required endpoint coverage,
fanout, actual placed-pin routed reach and containing physical rows. It can
emit a readonly row/rail requirements model with source-bound coordinates,
area and existing row descriptors that would be superseded. It creates no rows
or PDN and cannot qualify a timing run from missing physical infrastructure.

The actual regional pocket model (`physical/regional_pocket_model`) finds326
long legacy leaf sources; whole-footprint candidate reservations put all their
loads within53.610um direct pin bound. Other long regional sources number433,
with worst414.890um, exposing the original blocked-run boundary/pin offsets.
For the worst leaf, origin24322.680,8020.080um replaces an output at
21866.096,8015.355um next to the actual sink24323.802,8029.692um. This is a
buffer relocation into existing free geometry, not a macro relocation.

The opt-in `exact_region_bays` extension reserves the regional DME buffers while
building their topology and keeps their existing native insertion targets.
It removes the1200um route fallback, reserves boundary/pin-offset margin, and
rejects actual native direct wires>405um after placement. Regional geometry is
checkpointed before the spine. An actual isolated full `r343` region using the
same immutable full-shape source geometry places43 cells/29 sinks, maximum
actual direct wire212.858um, zero direct-reach violations. Its local root is an
explicit stand-in, so this is neither a full-spine nor a phase proof. Eleven
focused fleet tests pass. No exact-regional timing run is enabled until the
missing physical row/rail/PDN requirements are resolved.

The historical row/rail model in `physical/legacy_row_requirements` has38141
hard-free row segments,6.833547mm2 existing free area and25.309433m of horizontal
rail length, covering all109395 off-row historical clock cells. Compressed full
coordinates and their hashes accompany the readable summary. This is a readonly
requirements model for the old topology; it creates no physical rows or power
connections and does not approve a new candidate or expand the die.

The full exact-regional replay reached its actual occupied regional checkpoint:
35302 clock cells, zero all-clock footprint overlaps and zero regional direct
wires>405um (`physical/regional_full_audit`). It remains blocked by35285 missing
physical rows. The following spine planner then rejected a39-step continuation
from actual origin2020.140,5350.050 to bay2363.580,5400.000um. The preserved
`physical/spine_36diag/plan_fail.json` binds all763 required endpoints and the
complete failed path. The old route representation detoured through endpoint
cell centres and counted406.230um. Connecting actual endpoints to the first/last
interior vertices gives396.230um; a20um displacement gives416.230um and still
rejects. Twelve focused fleet tests pass with that actual failure regression.

`qwen_replay_spine.py` replays the entire required spine from an immutable
occupied regional ODB, preserving regional cells and native targets. A failure
keeps its partial stations and exact next-bay witness; a placed-pin failure also
keeps the actual ODB. A completed replay still requires the independent whole
footprint/net/endpoint/fanout/routed-reach/row audit, physical power and all
native phase references. It performs no STA or production admission.

The endpoint-trimmed full replay advanced to262 stations, then exposed a second
39-step gap: origin4477.680,5600.340 to bay4171.500,5510.160um bounds405.680um.
`physical/spine_endpoints_647` preserves that failure. The planner now reserves
explicit endpoint/pin margin:400um planned wire,340um blocked run, while the
actual placed-pin guard remains405um. Two1.620x.270 endpoint footprints can add
at most3.780um. Small existing standard-cell footprints also gain exact bay
refinement; they forbid their actual rectangles instead of an entire10um cell.
The occupied/fully occupied footprint tests and all12 focused tests pass.
The full regional checkpoint remains immutable during these spine-only replays.

Final998281bbb full-spine replay and independent actual ODB audit are in
`physical/full_spine_998`. All763 required regional endpoints are connected
exactly once with no missing/extra/duplicate endpoint. The actual candidate has
41835 clock cells (35302 regional,6533 spine), zero all-clock footprint overlaps,
spine fanout2 and7295 routed stages. Maximum actual placed-pin routed length is
400.964um. Regional maximum direct distance is364.058um, fanout12, with zero
direct wires>405um. The printed topology model's400um value is the planned
origin bound; the independent400.964um actual-pin bound is authoritative.

The audit remains FAIL:6522 spine cells and41807 total clock cells lack physical
placement rows. Timing, production phase and prefetch admission remain false.
The concrete readonly actual-candidate row/rail proposal contains16721 segments
in1.563948807mm2 existing hard-free area and5.792402988m horizontal rail length;
it covers all41807 off-row cells with zero uncovered cells. Compressed full
coordinates, the actual geometry manifest and hashes accompany the readable
proof/summary. No hard macro moves or die-outline expansion are required by
this geometry. ROOT must resolve the clock-corridor row/rail/PDN integration
before a timing retry; this is not a qualified clock or production Q certificate.

The original8de whole-spine replay also completed and is preserved in
`physical/old8de_full_spine_fail`: strict continuation(448,18) FAIL. All jobs
were collected; no earlier clock/control replay is left waiting for another
owner. The final source gives the topology-model bound its correct planned
name; no routing/placement behavior changes from the audited998281bbb run.

Power infrastructure is a substantive placement constraint, not a missing-row
metadata issue. `physical/clock_pg_blocker` measures the actual completed ODB:
all83670 new clock PG pins are unconnected,20873 violate the existing M8 supply
stripe clearance rule, and17283 clock cells violate the canonical1.08um macro
halo. The M8 phase/width is read from actual long core polygons (VDD edge4080DBU,
VSS edge8400DBU, width480DBU,8640DBU period), not inferred from a changed row
bounding box. The supplied mesh and deployed policy hashes are preserved.

Canonical `tools/qwen_split/die_tie_rows.tcl` treats every non-block/non-pad
instance as a movable constant, relocates it to a supply-safe row and rebuilds
all rows. Reusing it on this clock candidate would invalidate the405um proof.
The next actual source fix is PG-safe exact bay selection before regional and
spine reservations, fixed clock-row preservation in the constant/PG flow,
logical supply binding, literal M1/M2 contacts and safe upper-metal connections.
Power continuity/short and full405um/site audits must pass before timing. No
rows or rails were fabricated to convert this known physical blocker into a
geometry-only PASS; the live GEN and shared constant-PG tools remain untouched.
