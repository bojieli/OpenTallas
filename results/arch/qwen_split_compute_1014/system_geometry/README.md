# Qwen system geometry: whole connected groups

**Current coverage limitation:** the figures below compare the generated C17 assignment model, which still contains legacy SU and IO abstractions. They do not show a complete placement of the current actual RTL hardware. The real SU has 346 clock entries rather than two; its KV/embedding interfaces differ. Current static IO additionally requires five separate physical digital face rooms. `actual_su_coverage.json` starts the source-derived replacement inventory. Do not report the 1,637-rectangle picture as full-source hardware fit. The six controller defects described later were subsequently corrected by compute integration; seven actual producer joins remain open, and that correction does not repair the legacy SU/IO inventory.

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

## Current generated per-bit geometry, second batch

The authoritative current exporter (`9579cbd4f`) arrived and is frozen as `inputs/current_generated_pins.json.gz`, with uncompressed SHA256 `d365f8200e16beef575831464202de32f53f27bdf6a138fd83d66de52fe24a11`. It contains all 1,637 instances, 3,408 buses, 21,978 endpoints, 40 masters and 217,669 generated local pin rectangles. `current_pin_comparison.json` supersedes historical pin estimates above. The generated assignment pins are current, but physical masters, source integration and actual production IO topology remain unqualified.

The per-bit comparison resolves 3,327 of 3,333 data buses. Six buses reference missing actual generated CTLM ports: `uf_l0`, `uf_l1`, `uf_l2`, `uf_l3`, `xpf` and `xflt`. These are preserved as unresolved evidence and reported to compute integration; no invented aliases fill the gap.

| Arrangement | Summed per-bit pin-center HPWL | Worst actual assigned pin-pair distance | Decision at this gate |
|---|---:|---:|---|
| Wide27/Band1 reference | 1,741.694 M µm | 21.281 mm | Reference |
| Separated east F1 collectors | 1,786.150 M µm (+2.55%) | 16.414 mm (-22.87%) | Interesting critical-distance tradeoff; wider inter-collector traffic makes it unproven |
| Swap entire paired-band and VM/SU groups | 1,755.427 M µm (+0.79%) | 21.252 mm | Does not resolve global critical distance; west-side bwords become longest |

All preserve actual child dimensions, the same die area, and zero rectangle overlaps/outside. Neither tested move establishes a better system design. Actual activity, serialization, compiler critical-cycle path, all boundary traffic and physical channels are necessary for ranking. A long broad bus used once per programme and a frequently used serialized critical path must not receive identical throughput significance merely because they have equal width.

The next architectural candidate must reconsider the paired collector functions themselves: locate local reduction/input distribution by compute half, then compare the real remaining cross-half exchanges, exact arithmetic order, added storage/registers and fixed compiler schedule. This may justify wider channels, larger area or real pipeline cost. It requires actual RTL partition and programme evidence, not drawing a narrower link on the same old hardware. Compute integration owns that partition/port/clock join; geometry owns alternative group homes and all incident physical checks.

The KV owner also identified actual ECTL-C→head query paths of 623.9–1,023.4 µm that old parent-level checks hid; ECTL A/B/C genuinely abut across 648 µm. A two-copy 519-bit query fork requires four actual 263/256-bit banks, not one fictitious register box. Current two-edge placement pools have no joint solution with actual 13,410 obstacles and 485 µm reach; a system alternative must move the head/ECTL groups or add explicit pipeline stages and static timing. The lifetime/calendar constraint is also binding: 64 K acquisition groups can fit a minimum 98-edge start window, whereas fast acquisition of all 64 V groups is infeasible (worst 1,762 core edges). Placement must follow the redesigned paced V calendar.

Reproduce current exact assigned-pin comparison:

```sh
python3 tools/qwen_split/exact_system_geometry.py results/arch/qwen_split_compute_1014/system_geometry/inputs/current_generated_pins.json.gz results/arch/qwen_split_compute_1014/system_geometry
```

## Source-preserving structural SU grouping candidate

The actual hierarchy supplies a coherent starting partition: eight octet clusters. Each contains its eight lane cohorts (head, exp, reciprocal, rsqrt, lane relay/control: 40 roots), their two four-lane alignment groups (2 roots), and the corresponding regional eight-lane reducer (1 root). Thus each octet has 43 roots; eight octets plus the reducer tail and main controller account for all 346. This matches the existing eight-lane broadcast, four-lane alignment and eight-lane reduction hierarchy and preserves arithmetic order. The grouping adds no stages by itself. It is a connectivity partition candidate, with physical homes still absent; source hardening and actual lane/head/SFU pins, glue/alignment outlines, clock insertion and boundary channels must establish a viable arrangement. It is not an area-only fit of 265 known rectangles into an old box.

Conditional wider-NK sensitivity is recorded separately: retaining all 48 field columns and the actual DVM strip while increasing each tile 449.28→481.68 µm adds 1.5552 mm to die width and about 40.338 mm² at current height. The resulting approximately 881.053 mm² exceeds the current 858 mm² budget. A frozen 522.288 µm pitch would leave only 40.608 µm for a proposed 64.8 µm DVM leaf. Therefore any such safer tile requires a joint field/spine/height redesign or an explicit system trade; it cannot be hidden in the old narrow gap.
