# Qwen system geometry: whole connected groups

User charter, 2026-10-15: reconsider the complete Qwen ROM system placement, including compute fields, reduction trees, paired BAND collectors, VM/SU/control, KV/system die and external seams. Place bandwidth-critical and latency-critical communicating elements together. Compare legal facing-pin orientations. Existing wide27/Band1 placement is a reference, not a frozen global topology. Local moves cannot establish system optimality. Added area and real pipeline stages are explicit measured tradeoffs, never silent schedule changes.

This first batch compares three coherent arrangements at the same 840.715 mm² compute outline, preserving all 1,637 current instance dimensions. The common-scale SVG and PNG show actual rectangles, including the 768 compute tiles. No production placement or live allocator has changed.

- Reference: wide27/Band1-MX placement.
- Distributed east collectors: move all three F1 collectors 5.104 mm toward the east compute field; shift the middle collector 635.04 µm vertically to clear actual VM. This tests whether shortening the obvious long east-side wires is sufficient.
- Swapped whole spine groups: move all paired BAND/port/serializer groups 4.8384 mm east; move the coherent VM/SU/sequence/control/CBUF/CROM group and clock/reset receiver pair 2.37168 mm west; move the four-leaf upper tree east. This preserves the very wide F0/F1 links and the internal VM/SU grouping.

All three have zero rectangle overlap/outside errors. Rectangle legality is not macro halo, pin escape, routing, timing or clock qualification. The swapped arrangement changes 42 instances and tests a real group rearrangement; it is not an adoption recommendation yet.

The complete current geometry-only graph covers 3,333 non-clock/reset buses with zero missing instance endpoints. Its weighted center-HPWL is 2,005.850 million bit-µm at reference, 2,051.099 million for separated east collectors (+2.26%), and 2,004.619 million for swapped whole groups (-0.061%). These are coarse geometry diagnostics, not actual pin or routed lengths. The broad graph establishes why moving a visible long wire alone is insufficient: the collector pair exchanges 2,048-bit ty, 2,050-bit fragment, and 2,213-bit request buses per band.

Port graph reconciliation found 824 retired bus names, 50 new names, and changed endpoints between the historical endpoint graph and current model. Only 657 of 1,509 historically pin-resolved buses match the current bus name, width and endpoint instance multiset. The other 852 resolved historical edges are excluded from current comparisons. Even the 657 require current port-level validation; name/instance matching does not prove port identity. The full current exporter requested from compute integration is the next gate. Historical 19.763 mm bword distance and earlier apparent improvements must not be reported as current whole-system results.

KV/system is explicitly in scope: current selected-native-ASTK candidate is 10,841.472 × 24,587.28 µm, 2,362 parent instances, with 180 selected non-PV ASTK children fitted. PV/collector/clock-return homes and the actual 583-bit compute/KV seam remain open. KV owner supplied actual engine-head pin/obstruction snapshots and closed bank pin plans; those must join the system graph before a combined recommendation.

Next: ingest current endpoint/real-pin export, derive communication groups without preserving old spine boundaries, compare distributed reduction/collector hierarchy as well as whole-group relocation, provide separate wider DVM head-row and safer leaf-strip alternatives, then measure actual per-bit hops/relays, clock phi−R, cuts ≤0.60, halos/obstructions and static programme cost. Do not run another expensive allocator on a historical graph. Physical orientation admission must transform actual pins, clock roots and obstructions, and must respect leaf symmetry/legal orientation; a mirrored picture alone is insufficient.

Reproduce from repository root:

```sh
python3 tools/qwen_split/system_geometry.py --historical results/arch/qwen_split_compute_1014/system_geometry/inputs/historical_ports.json --current results/arch/qwen_split_compute_1014/system_geometry/inputs/current_geometry.json --projection results/arch/qwen_split_compute_1014/placement_repack/wide_band1_projection.json --pin-dir results/arch/qwen_split_compute_1014/c17_source_pins --pin-dir results/arch/qwen_split_compute_1014/c17_band_quarter_pins --out results/arch/qwen_split_compute_1014/system_geometry
```
