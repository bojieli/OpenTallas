# Joint landing API and generator contract, before implementation

This specifies a proposed opt-in backend. It is not a validated implementation. Existing `ot_pl_land_w/r`, `ot_pl_land_chunk_w/r`, existing consumers and generator defaults remain byte-identical until each consumer accepts a priced source contract.

## Source protocol

One `ot_pl_land_mem` owns a logical source-to-one-reader crossing. Width W includes every coherent control/payload/epoch field that must arrive together. Parameters are explicit W,D,K, source pipeline depth SW and destination pipeline depth SR; no inferred K or silent phase default. Clocks `ck_w` and `ck_r` must have an admitted hardware relation. Data `i[W-1:0]` is sampled on the source clock; data `o[W-1:0]` is the final registered destination value. The interface has no ready, stall, credit, training, implicit reset initialization or variable-latency outcome.

Reset inputs are explicitly grouped equal-age leaf vectors `rsi_w[GW-1:0]` and `rsi_r[GR-1:0]`, not one unconstrained scalar broadcast. The generator must own the equal-depth regional reset forest that supplies those leaves. Group counts, leaf identities and exact first-active-edge offsets are recorded. A scalar compatibility wrapper is permitted only when its actual mapped fanout is <=32 and its epoch contract matches; buffering the scalar does not change the transitive census.

An unimplemented candidate budget is <=4 macros per counter/enable group, <=16 data bits per final-valid replica, <=16 reset-tree children per stage. These are design targets, not measured bounds. Every source/data/address/reset/valid/warm/output driver still requires the complete native mapped census. The storage bank remains one logical W*D object for the >2048-bit SRAM rule, regardless of control/data slicing.

All words emitted after reset must equal the original epoch value or the original specified zero. SRAM arrays start arbitrarily. Writing/reading a reserved zero row is allowed only with an explicit hardware reset duration and verified write-to-read timing; behavioral model initialization cannot establish that duration. SRAM macro read data followed by a combinational valid mux alone does not meet the registered output boundary requirement.

For multicast, instantiate one read storage copy per independent destination clock. A shared source reset/counter is allowed only after fanout proof. Each copy has the same logical producer epoch and data; copy identity is explicit in the record. A different-clock second read cannot be time-multiplexed onto a one-read-port macro without a fixed proven schedule and a newly priced interface.

## Exact edge ledger

The generator must provide, per source bit and per reader: original source-sample edge, SRAM write edge, SRAM prefetch edge, final capture edge, destination-use edge and first valid epoch. SW/SR and an increased K are charged exactly once; original E+1 must not be retained as an independent charge if the new total already replaces it. New output age equals the complete event-edge ledger, not a parameter name.

HBM's old D2/K1/E1 +2-edge crossing cannot be represented as synchronous SRAM plus final FF with the same unsupported same-epoch read assumption. An accepted replacement must report the actual added age and re-solve all parent joins. QW/S81 K2 lookahead is conditional on a real phase/reset certificate; it is not enabled from nominal PLL frequency. For each coherent bundle, the same source epoch, read epoch, reset age and final age apply to all fields.

During in-flight reset, every allowed source/destination reset ordering must produce the same defined zero/first-use behavior. Epoch wrap and source and destination counter restart are part of the proof. The design must never reinterpret one cycle's data as a later valid epoch to get a pass.

## Generator input and output binding

Suggested new explicit input object `landing_backend` contains backend version, exact selected master/view SHA, per-crossing identity, per-reader replicas, phase-certificate SHA, endpoint-certificate SHA, reset-leaf forest, SW/SR/K/D and an accepted edge/cost ledger. Missing proof or an unsupported crossing fails generation. It must not silently fall back to FF storage, midpoint placement, a different macro, an implicit K or a slower clock.

No-backend/default generation must emit byte-identical RTL/SDC/record/bench to the source-pinned baseline. For opt-in migration, the record binds original net name, source driver expression and ordered reader port expressions; source ring_of sharing identity; bit ordering; width; replica count; instance names; clock/reset leaf identities; every generated macro/hop/FF; exact added edges and all parent offsets/pads. A before/after port map must show no functional tie, truncation, omitted status, duplicated reader or changed bundle packing. A retained diagnostic original-bank implementation is not an accepted physical fallback for >2kb storage.

SDC is regenerated from actual storage/hops and exact clock domains. The old bank-wire multicycle exception must not survive on newly single-cycle macro-output or pipeline paths. Existing boundary constraints retain their numeric requirements. The generated parent audit must recognize the joint module's actual clock pins separately; classifying a two-clock joint module as one-region logic would hide a CDC path and is forbidden.

## Endpoint certificate schema

Each crossing needs exact source and reader pin identities with indexed bits, source RTL SHA, linked mapped-view SHA, placed ODB SHA or explicitly approved immutable placement artifact, child instance placement/orientation, and pin coordinate transforms. Grouping by a region centre is insufficient. Include each proposed macro instance/origin/orientation and exact w-data/r-data/w-clock/r-clock/addr/enable pin locations and master LEF SHA. Clock routes, reset routes and functional data routes are distinct recorded obligations.

For every consecutive registered/storage endpoint pair, compute actual Manhattan distance and assigned path class. Ordinary one-cycle hops require <=405um and real timing; a landed holding path requires its own proved age/window. Record the longest bit, not only a bus centroid. Region-centre estimates remain lower-fidelity planning inputs, explicitly labeled unqualified. Where no actual endpoint artifact exists, the model returns BLOCKED, not a fabricated coordinate or physical PASS.

The certificate includes area for macros, final/copy/relay FFs and control/reset replicas, channels, clock pins/trees and resized parent; output ages feed the actual compiler dependency graph. All pricing is prospective until direct behavioral positives+causal mutants, native32/storage/boundary/reach, phase/first-use proof and physical review pass on the exact source.
