Private exact FDI source extraction, no provider or production adoption

Retained inputs at intel1:/srv/opentallas-scratch2/claude/codex-kv-fdi-0222/parent_size/: host_elab.json, native_cut_profile.json, inverse_inventory.json and rtl/kv3_hub_Wi_part_bound.sv. Original hierarchy recovered from epyc2:/srv/opentallas-scratch2/claude/codex-kv-wi-inventory/inverse_inputs.tar.

Run prepare_parent_size.py DIR before emit_parent_size.py DIR and join_parent_profile.py DIR. The first resolves exact hierarchical paths for all existing HR members, replaces only the full u_fdi_join instance with the unqualified ot_kv_fdi_join_rf model, and lowers the remaining source with stock Yosys. The emitter uses the original exact inverse pin inventory to preserve all21HRchildren, every sibling and all133outerports. The join adds the unchanged guarded six-parameter production wrapper. Neither a flattened cell label nor an inferred ownership rule defines this cut.

run_parent_synth.sh documents the source-bound ASIC mapping. Only Yosys mapping/count is intended. The aggregate make synth later refuses ODB assembly because the unqualified models have no physical LEFs; this is recorded, no physical view is fabricated. source_bound_size.json records17,500standardcells +22blackboxes,2,594.467260um2 excluding children. This is not final fit: parent landing/station/clock/reset buffers and a signed actualFDIview are still required.

Physical FDI source/proof/model are in the parent fdi_1108 directory. New input stage coherently delays both valid-only streams by1edge and keeps native FIFOdepth16; no ready/credit ports exist. No production plan was changed.
