# DIE-QC-44: OpenRCX on the fixed (pre-routed) QC die clock wires of complete_pg/provider.odb -> clock.spef.
# Only nets with wires are extracted (the 44,591 fixed clock nets); GRT-only nets get their RC from estimate_parasitics later.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_db /s/codex-qc-2249/complete_pg/provider.odb
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $P/rcx_patterns.rules -no_merge_via_res
write_spef /s/die-qc-44/grt/clock.spef
puts QC44_RCX_DONE
