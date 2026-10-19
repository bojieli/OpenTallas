# Dedicated HBM joint corridor — complete source MODEL, physical HOLD

The finite NEW model contains all **810 frozen forest-boundary reset pins**, **2,263 kept native stations**, **494 local two-FF face pairs**, and **2,262 recorded trunk polylines**. Maximum conservative registered reset contact span **402.6um**, clock contact span **400.286um**, BUF/INV-transparent reset loads **19**, and direct clock loads **6**. It preserves every original failed forest artifact. No prototype RTL, mapping, placement, forest replay, engine, main/shared-helper activation or adoption was performed.

The model is a positive **home-reservation / finite topology** result only. Every actual TT/FF phase, native min-CQ at the new load, legal die std-row availability, continuous native layer access/OBS, supply connectivity and routed track/via occupancy remains NULL. This is not a PG, routing, timing or reset-release PASS.

## Exact boundary and inventories

Inputs are the immutable forest_codex9d5a2c350 manifest/contract and GEN2c case_a run.tcl/die.v already hashed in 5b6145c10. `report.json` pins their actual SHA256 and every consumed master LEF. `sinks.json` records instance/port/bit/domain/source/native contact and the first candidate branch; the final branch ownership is in `compressed_topology.json` through its exact sink indices. All810 contacts resolve without errors. `row_ownership.json` records the exact frozen reset_rows.py parent/depth/lag/head graph.

**810 is not the entire HBM reset-pin population.** The contract has3,793 hb_ckgen-owned HBM reset pins; frozen row contraction removes2,983 row children from the forest boundary. All row ownership is preserved. This proposal covers the810-boundary forest and does not silently qualify the downstream rso/rs native interfaces, row reach/fanout or existing release offsets. Those must remain in the composed reset and first-use proof.

Fleet inventory:57,211 placed outlines,76,233 actual clock placements/declarations (60,464 BUFx24 and15,769 BUFx12f),190 consumed placement masters. `placements.json`, `clock_cells.json`, `consumed_lef_pins.json` and all original source bytes remain on the admitted data-local fleet host; hashes/sizes are in `manifest.json`. `macro_supply_roles.json` finds56,226 exposed native PG terms, but **125/190 abstracts expose no PG pins**. This is an explicit missing-supply-interface HOLD, not a complete native PG pass. Existing clock cells have152,466 VDD/VSS terms by their actual two masters. No routed conductor/via snapshot exists.

The new source is genuinely **hb_ckgen.por_hbm**, native contact(11284.116,15487.242); dedicated clock input binds hb_ckgen.pll_hbm. It does not infer a predecessor instance from the historical failed coordinate(12761.158,19794.988), and it does not reuse the seven-home local clock spur as a16.43mm reset path.

## Deterministic construction and finite failures

The immutable first302.4um lattice candidate has3,685 32.4um-square homes;2,887 intersect frozen outlines/clock envelopes. It is REJECTED, with exact conflicts retained in reservation_ledger.json and MODEL.png.

A separate exact rectangle-inflation study uses5,504,482 sampled centers at10.8um spacing. The old32.4um body plus1.152um halo has1,600 components,125 boundary pins lacking a home within350um, and only59 pins accessible from any source-admissible component. This is a conservative sampled-home graph, not a proof that continuous geometry is impossible.

The NEW native strip uses a body no larger than8.64×.54um plus1.152um halo per side. It yields1,600,160 free sampled centers and4,584 center components; all810 pins have a home within350um. Only160 pins lie in source-admissible components. The potential visibility graph therefore permits bounded wire overflight separately from home placement. A conservative350um diagnostic reached791 pins; the final **402um center bound is derived as405um minus3um native reset contact allowance**, rather than a timing or phase relaxation. It reaches all810 through221 component bridges, maximum center span399.6um. The complete graph is deterministic and finite; no old allocator, root-count retries or adaptive forest variants were called.

**Free centers are not continuous free channels.** Adjacent sampled centers may straddle thin obstacles. Every connecting segment, including short ones, retains native-layer OBS/PG qualification OPEN. Clock envelopes block native cell homes; they do not automatically block every metal layer. `nativebound_visibility_bridges.json` preserves each bridge and its NULL layer/PG qualification.

One BFS through the potential graph yields39,159 distinct uncompressed station centers. Deterministic compression preserves every branch, target and component-bridge endpoint and bounds every retained polyline. The final2,263-station tree retains all810 endpoints and494 leaf pairs. `compressed_topology.json` records every actual model center, parent, children, routed polyline, depth, sink indices and fanout count. There is no combinational buffer chain masquerading as a registered hop: each retained station has a genuine two-FF reset pair.

The final standard-cell body is8.424×.54um (156 .054um sites, two .27um rows), a subset of the already checked8.64um body. Its full halo envelope10.728×2.844um fits disjointly at distinct10.8um grid centers. Native bodies and clock/macro obstacle envelopes do not overlap. Existence of the corresponding die legal rows and orientations is still unproven.

## Genuine native source equation and cost

`native_lib_roles.json` gives TT/FF file hashes, ALL primitive pin roles/functions/caps and each timing arc's table index domains. `prototype_model.json` gives exact LEF pin rectangles/PG roles. The native masters are BUFx12f, DFFASRHQNx1, INVx1 and TIEHIx1, all ASAP7 RVT. No synthetic clock output is declared on the old hbfd_rrl masters.

Proposed station source equation, with genuine native cells:

- `clock_out = BUFx12f(clock_in).Y`; this is an actual nativeY contact feeding the local FF clocks and the next station's actual bufferA.
- Native FF has `QN=IQN`, `next_state=!D`, `preset=!RESETN`, `clear=!SETN`. Tie SETN high. FF1.D=1; FF2.D=INV(FF1.QN); each RESETN=upstream_reset_n. Positive reset release is `INV(FF2.QN)`.
- A distinct leaf pair implements the same equation for each group of at most24 genuine boundary pins. No borrowed serial/stream station or ideal clock phase is used.
- Each trunk output drives the actual two RESETN inputs of every child pair and every local leaf pair. The complete finite model's maximum is19 actual nontransparent loads; clock maximum6. No reset/clock name exemption hides a driver. Actual mapped original+new native all-driver census remains required.

Exact compressed cost:5,514 ASR FF,5,514 INV,2,263 clock BUF,2,263 tie cells; native area3,024.31482um2;31,108 new PG MTerm bindings. No SRAM/coherent indexed state or useful payload bandwidth/MACs is introduced. All added clock capacitance and native table-domain/transition qualification must be evaluated at actual routed loads, not at a zero-load table entry. The source PLL's extra true load and existing tree ownership are part of that qualification.

A trunk-only coupon fits4.32×.54um at49.4% native fill; the largest trunk+leaf coupon fits8.424×.54um at43.9%. The full common reservation uses the larger body even where a leaf is absent; its lower average utilization is not disguised as a qualified tile floorplan.

## New PG/channel reservation recipe — MODEL, not existing metal

Every branch reserves six tracks: forward clock, registered reset, two VSS shields, one VDD and one VSS supply; .192um candidate pitch gives1.152um width. M6 horizontal/M7 vertical is a proposed layer assignment only. Native OBS, spacing, via access, neighboring reservations and actual technology qualification are OPEN. At each bend reserve all six via stacks and retain their supply/signal identities; track sharing cannot cross supply roles.

Each two-row coupon uses actual M1 VDD/VSS rail roles: row0 R0 has VSS at0 and VDD at.27; row1 MX shares VDD at.27 and has VSS at.54. Rail extents include the native9nm overhang. New M1 straps must connect every native terminal, with separate vertical M2 VDD/VSS access, at least three rail-to-access junctions and one complete upper-layer access stack per supply. Exact cut multiplicity, via enclosures and routable landing positions remain NULL until the actual technology recipe is bound. All31,108 proposed terminal bindings must be present before protection, then pass native MTerm-existence/type plus full conductor/via connectivity checks. Neither an overlap of modeled rails nor the count of PG names proves a connection.

## Phase, pulse, source-relative age and compiler price

HBM period is1024ps. Actual TT/FF source/landing phase extrema are NULL. For every predecessor i→j use true edge identity and verify at both corners:

`CQ_i(min)+reset_wire(min)-max(C_j-C_i) >= removal_j+25ps`

`CQ_i(max)+reset_wire(max)-min(C_j-C_i) <=1024ps-recovery_j-60ps`.

Within each native FF pair, prove actual min/max data arcs, hold and uncertainty, including the inversion and native clear/preset semantics. Buffer forwarding alone does not make an extra release edge. A same-edge capture or aperture ambiguity invalidates a fixed age; implement a genuine characterized half-cycle contract or change the source structure before granting a fixed compiler age.

The final tree has maximum179 retained transport stages. **362 HBM edges /370,688ps is only the conditional two-edges-per-stage plus two-edge-face bound**, not an observed release age. Actual compiler POR age remains NULL. Compose downstream row depth/lag and existing head offsets; do not overwrite the frozen reset-row contract. A prototype must prove reset-state valid signals remain non-producing until the global first-use boundary before permitting unequal early releases. Every genuine additional startup edge costs1024ps. Runtime token delta0 is conditional on startup finishing before priced work, not a current achieved-rate claim.

Raw assertion must reach every clear pin with clocks stopped, satisfy minimum clear pulse after the longest actual assertion chain, survive reassertion in flight and cold unknown FF state, and preserve domain ownership. Do not mask recovery/removal or use POR false paths as evidence.

## Concrete smallest next source-prototype proposal

Only after ROOT review: add an isolated default-off station wrapper implementing the exact native equations, an independent truth/age/no-zero-init/stopped-clock/pulse/reassertion bench, and the exact2,263-node generated graph plus810 sink ownership manifest. Keep all production sources/defaults byte-identical and retain the original810/3,793 distinction. Test a minimum component with source+two transport stations+one local face pair, then source-level graph composition; no full die simulation is needed to establish the mechanism. Causal controls must catch inverted native QN, missing stage, same-edge release, short pulse, clock-stop assertion failure, ownership swap, omitted row offset, reach406um and fanout33. Numerical/functional tests do not clear physical HOLD.

Before any physical engine: resolve native legal rows/clock delivery, all old+new native PG interfaces, native-layer OBS/channel access, exact source load, full pin census and TT/FF min-CQ/recovery/removal/phase. The future failure schema is `failure_snapshot.schema.json`: serialize pre-candidate and pre-restore bytes/hashes, all reservations/host owners, source/target native contacts, full clock/PG/track/via inventory and the concrete failing constraint **before restoration**. This schema describes a FUTURE new run; it is not recovered original evidence.

Checklist: pins/two-stage face SOURCE MODEL; reach and fanout finite native-contact MODEL; logic depth/native timing HOLD; runtime storage not added; candidate home rectangles PASS but actual rows/PG/channel HOLD; native clock delivery/TTFF phase HOLD; compiler startup age conditional/HOLD. No READY/SAFE label or engine grant follows.

Fleet jobs were unpinned/data-local via ot-run, maximum measured inventory RSS1.34GB under8GB admission. All jobs terminal; original inputs/source helpers untouched. Original first3,793-versus810 assertion failure and every intermediate candidate remain immutable in this packet.
