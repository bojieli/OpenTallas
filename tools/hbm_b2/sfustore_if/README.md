Opt-in SFU SRAM interface successor

Legacy source and default recipes stay unchanged. `recipe.json` is a coregen recipe override for the existing plan master, with the separate `*_if` source top. The actual provider macro/port convention stays unchanged. Do not use the old sfustore physical kit as this successor.

`run.sh OUT` runs the smallest full-width bank against the real behavioral SRAM. `count_ff.sh OUT` counts logic against the exact provider-header blackbox; `pin_ff_gate.py OUT/physical.json --out GATE.json` requires782 distinct FF endpoints. `gen_geometry.py --out GEOMETRY` emits reproducible shared macro placement,1829 public pins,12512 named FF targets, summary and image. It uses the committed real LEF and old pin-table bytes.

Adoption is one common311.04x354.24um master and matching pin table for the two B2 hub placements. Recompute parent per-bit mapping/reach in that same plan batch. Retain the ordinary outer face-shell cycle charge separately. Added bank/tile data cycles are0, added FFs704/11264; DFFHQNx1 area estimate3284.5824um2/tile, plus actual mapped combinational/clock/hold cost. SRAM capacity/bandwidth unchanged.

For coregen placement, use generated macro_placement.json and instance format `u_core.g_bank[{k}].u_bank.u_data.g_read[0].u_m`; the ordinary face-shell generator prepends `u_fcore.`. `anchors.tcl` belongs after the floorplan/macro placement and before global placement, with SFUSTORE_IF_ANCHORS pointing to generated anchors.tsv. It binds live pins to actual mapped FFs and fails closed on merges, missing/oversized FFs or missing rows. No clock/reset/net connectivity is edited.

P&R/STA remains held until the actual mapped source kit and clock/PDN/channel geometry are rendered/reviewed. The current review is results/geom_review/sfustore_if_20261025/review.md. A passing anchor model is not a SIGNED view.
