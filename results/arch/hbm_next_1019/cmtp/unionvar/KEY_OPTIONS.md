# Source-derived key options (architecture candidates)

The source study reads the exact original 120-trace router capture and drafts (the two SHA256 values match the existing MTP-STATS evidence). Rejected verify lanes retain the documented decorrelated same-trace estimate; no new exact routing capture is claimed. N6 has mean U=24.593; independent four users U=21.885. A key is sampled at the route boundary, before expert work.

All proposed bounds apply to **every SM**, not an average SM: an IDX row-table expert cardinality c_u counts all positions needing that expert. Any SM's rsel row subset has at most c_u entries. A global Cmax is therefore an upper bound even if the physical mapping sends only subsets to individual SMs. Each SM still needs its actual local output-row ceiling/K shape and worst broadcast/load/publish timing; a model average over SMs cannot replace those bounds. A native driver must prove this mapping against its physical SM dispatcher before adoption.

| Key | Static body bound | Legal N6 / N4 keys | Mechanism/cost still owed |
|---|---|---|---|
| U only (implemented component) | reserve N rows for every expert | 31 / 19 | 3014 MTP / 926.6 per user; native dispatch/residency open |
| U, Cmax | reserve Cmax rows for every expert | 118 / 44 | max reduction during IDX table generation, extra key/bank selector; no expert reordering |
| full cardinality histogram h1..hN | exact count-class kernels, grouped by c | 2432 / 169 | bounded on-chip grouping/reordering of list+row tables, or an ordered kernel-selection/prefix plan |
| full ordered c_u vector | exact count-class kernel cadence in original union order | 26,649,774,581 N6 vectors (823,051,596 at U24) | whole-profile bank duplication impractical; factor kernels and build all start metadata before loop |

Expert order can change without changing arithmetic only if each result retains its own (position rho, top-k rank kappa) cell and the final routed sum remains in each position's ascending-expert-id order. The current golden combine order must remain unchanged. Reordering just the expert IDs without their matching rsel tables is incorrect.

The U,Cmax histogram is source-derived at the layer boundary. Among verify union experts, the layer's max bucket C1/2/3/4/5/6 is 0.1/9.0/29.0/31.2/20.3/10.4 percent (weighting each layer by U). Four users' C1/2/3/4 buckets are 16.8/66.7/14.9/1.7 percent. Unlike the old individual-expert histogram, these fractions price the **worst expert of each selected layer** for every expert in that layer.

For N6/P3, c_u in 1..3 takes one pass, c_u in 4..6 two. Any U-only shape has at most `floor((36-U)/3)` two-pass experts because every union expert needs one membership and a second pass needs at least three more. Thus aggregate passes are at most `U+floor((36-U)/3)`, e.g. 28 at U24. The current ascending expert stream cannot use this aggregate bound as per-expert slots: any expert may be the six-row one. Grouping the one-/two-pass lists or computing all fixed start offsets from the ordered cardinality vector before launch would be a new mechanism. The bound alone supplies no RTL performance credit.

## Capacity and boundary work

The unchanged HGI-1R record suffix bytes depend on U, not Cmax. The current 10,158,080-byte HBM record bank can therefore be shared by all Cmax timing variants. Naively duplicating whole record banks for 118 keys would use about 38.7 MB, but that duplication is unnecessary. Timing-event banks still need their own capacity. The current L2 maximum padded event stride is 256 words, so 118 max keys need at most 30,208 x 81 bits (305,856 bytes; AW15), before sharing event tails. Direct full-histogram timing banks need at most 622,592 x 81 bits (~6.3 MB, AW20) for L2. These are proposed SRAM budgets, not installed memory or measured silicon area.

A factored ordered-profile candidate avoids the Cartesian timing bank. Preinstall each local (layer type, c=1..N, w1/w3/w2) expert kernel, then routing emits c_u and a fixed prefix-preparation engine computes all start offsets before the loop. Keep ascending union order, so no expert-table reorder is necessary. Example metadata for U<=36 is 36 x (3-bit cardinality + 32-bit start per loop) = 2,412 bits (302 bytes) for two loop-start arrays, plus 36 expert IDs (324 bits) and validation/control. Using two parallel prefix accumulators and computing one pair of prefix entries every three edges is 108 cycles per layer as a **candidate**, not measured hardware. All choices must be latched before the first expert launches; no ready/credit or mid-loop duration decision is permitted. A safe implementation must include SM HBM fetch, x-load, compute, publish, collective/gather and loop-two dependence in each kernel's bound, and retain real per-SM layouts.

For a conservative resident event-store budget, preinstall six c variants of four event-kernel references per layer for all 40 layers: 960 x 81 bits = 9,720 bytes before addresses/durations, plus common prefix/suffix control and native descriptors. This count prices only kernel references; **it does not establish all native unit programmes fit**. The actual loader, unit descriptor stores, macro area and TT/FF (SS sensitivity) timing remain unpriced. A fixed prefix preparation could use a 40x6 duration/offset table plus per-SM shape-specific constants, but must not silently replace actual expert kernels with a model callback.

The candidate reprice scripts report U,Cmax reservation and exact-cardinality kernel work separately, with main-layer prep exposed. Final candidates use the structural uncaptured bound `min(N, topk*N-U+1)`: the current no-sharing N5/top3 draft U15 has c1 exactly. Initial N-row conservative prices remain preserved. They do not establish native descriptor execution, store residency, loader cost, or an accepted token rate.

## Existing SRAM macro budget (not implementation evidence)

The repository's `ot_sram_1r1w_1024x256_m2_r2c2` abstract is 174.744 x 70.470 um (0.01231420968 mm2), 1R1W with bit write masks. Two 81-bit events fit one 256-bit word. At the component's AW14 capacity, eight macros store all 16,384 events (0.0985 mm2 macro area, roughly 0.179 mm2 slot at 55% fill before extra wiring/control). The used L2 7,936-event fixture fits four macros. AW15 max-key capacity needs sixteen macros (0.1970 mm2 macro, ~0.358 mm2 at 55% fill). Forty such layer-resident stores use 640 macros (7.88 mm2 macro / ~14.33 mm2 at 55% fill) and avoid per-token layer reloads; this is an upper budget, not a floorplan or a claim that all native descriptors are resident.

The modeled macro clk-to-Q is TT 544.81 ps / FF 450.74 ps; SS 691.77 ps is sensitivity. FF setup/hold are 24.69 / 19.67 ps. Current HANDOFF section 2 signoff is TT setup + FF hold >=0. No current component timing route is supplied. Place local capture flops beside the SRAM outputs and budget the half-word mux/bank mux, region crossings and launch output under that policy. One extra pipeline stage is an available structural option if the routed budget needs it; no unsupported SS reclose is required.

One event write per configuration edge gives a fixed 16,384- or 32,768-edge full-store installation budget per layer; with 40 AW15 stores it is 1,310,720 edges (~1.092 ms at 1.2 GHz), paid at resident-program installation. The existing masked SRAM write port supports the two half-word event writes without a read-modify-write. Configuration remains idle-only. This is only the event-store path: actual host/loader payload transport, commit/validity checks and native descriptor/engine-programme writes must still be added. They cannot be assumed free or replaced with credits. No gate may adopt the current runtime-indexed behavioral memory as a production program store.

Prefix metadata also exceeds the safe-design 2 kb flop threshold: store it in SRAM. A possible packing uses the 94 spare bits left after two 81-bit events per 256-bit word: each expert needs two 32-bit starts + 3-bit cardinality + 9-bit ID = 76 bits. Fixed pre-loop masked writes and later metadata/kernel reads must have an explicit one-1R1W-port schedule; host configuration remains disabled during both phases. No behavioral metadata array is proposed for production. This packing is a resource option, not an implemented port/latency proof.

## Conditional rate comparison (not adoption)

| Candidate | AR | MTP work only | Main-model prep | MTP with that prep | Four users with main prep |
|---|---:|---:|---:|---:|---:|
| Existing U-only conservative component | 1,967.8 | 3,014.1 | new physical installation/dispatch unpriced | not adopted | 926.6/user (before new costs) |
| U,Cmax | 1,967.8 | 3,144.0 | 1 cycle/layer assumed | 3,143.92 | 1,020.72/user |
| Factored ordered-cardinality work | 1,967.8 | 3,380.3 | 108 cycles/layer assumed | 3,370.44 | 1,035.72/user |

The profile candidate is the useful next mechanism to prove; Cmax alone misses the MTP target. The profile result has only 0.19% model margin over 3,364. Its preparation is an explicit unmeasured architecture assumption, not RTL throughput evidence. The pooled S2 expectation still requires exact per-key/kernel bounds and native local SM mapping, SRAM ports and actual descriptor stores. Draft/seed preparation/installation beyond the structural body reservation remains unpriced; neither physical area nor boundary wires are hidden in the original die price. No rate adoption or target waiver is justified by this table.
