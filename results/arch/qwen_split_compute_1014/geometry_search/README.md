# Qwen connected-geometry search, 2026-10-15

This is a proposal against the primary wide27/Band1-MX placement, not a production geometry change or a route qualification.

The source-bound historical endpoint graph resolves 1,509 point-to-point buses using assigned actual pin ranges; 2,598 non-clock/reset buses remain unresolved. Resolved families are tree_block/tree_spine. VM, SU, res_ser, IO and retired aggregate-up4 peers need current pin and topology completion before a global optimization claim. Actual C17 rectangle sizes/positions are overlaid before Band1-MX changes; baseline has zero overlaps/outside rectangles. All lengths are conservative Manhattan pin bounding spans, not routed wire length or exact per-bit pairing.

The strongest independent known-pin orientation proposal is `sp_port_tiles_2_f1` MX. Its total known incident bound falls 55,940,615.232 to 53,794,705.440 bit-um, a saving of 2,145,909.792 bit-um (3.84% incident, about 0.24% of resolved global cost). All historical non-clock/reset incident nets resolve. The artifact records every changed leg and all 49 transformed clock entries. This flip has tradeoffs: bword_47 grows about 351um and bword_43 about 150um; several local BAND/port links improve considerably. Native hierarchical orientation, clock phases, pin escape, actual relay count and cut capacity are still open. No lead layout has been changed.

Coherent +432um-Y translations of Band1 and Band2 each reduce the known bound, but have 12 unresolved incident nets each. They are diagnostic proposals only. More aggressive array-level shortening should examine the long bword routes from far-east compute tiles to central port slabs: the worst known connection bword_46 spans approximately 19.763mm. Local mirroring alone cannot remove this global topology cost.

The DVM widened-column audit finds zero W clearance and 0.648um E clearance for each of 48 columns. Do not interpret the 0.648um total as balanced clearances. The widened leaf/column physical views are absent from these inputs. The old leaf recipe's 5.4um macro halo is an internal recipe parameter; applicability at die boundaries must be established, not assumed or waived. No lateral relay sites or pin access are qualified by rectangle fit. Upper metal crossings and registered abutting faces may still be feasible with actual obstruction/pin views.

Reproduce:

```sh
python3 tools/qwen_split/geometry_search.py /tmp/claude-1000/qsc/v13_dump.json results/arch/qwen_split_compute_1014/placement_repack/wide_band1_projection.json --actual-model /tmp/qwen-c17-wide.json --pin-dir results/arch/qwen_split_compute_1014/c17_source_pins --pin-dir results/arch/qwen_split_compute_1014/c17_band_quarter_pins --out results/arch/qwen_split_compute_1014/geometry_search/search.json
python3 tools/qwen_split/dvm_gap_audit.py /tmp/qwen-c17-wide.json /home/ubuntu/wt/qwen-split-compute-1014/results/arch/qwen_split_compute_1014/dvm_column_candidate/geometry.json results/arch/qwen_split_compute_1014/geometry_search/dvm_gap.json
```

Input hashes are recorded; preserve those snapshots when collecting the lead's full allocator. Four focused regression checks pass, covering extent/mirror geometry, missing-endpoint refusal from known cost, unduplicated cost/orientation restoration, and asymmetric lateral clearance with Y-overlap filtering. Full relay allocator PID1201509 has not been mutated or restarted.
