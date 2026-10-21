# hbm_su_static_kind2_rg_1020 kit-scoped (copied by HBM-KIND9 from hbm_su_qcore_r13_1020) SYNTH_CANONICALIZE_TCL (HBM-QCORE9 10-20, DRIVE-HBM decision): Codex FP6 alias + splitter
# flow (results/arch/hbm_qcore7_native32_1020/fp32_copy_canonicalize.tcl, codex/hbm-qcore7-native32-1020 @d73bee5f7),
# unchanged except for the kit-local path of copy_aliases.py.  ot_hdc_fp32_add_n32 marks its exact copy families
# (* keep, ot_rst_split *) on generate-scoped [bit] wires the splitter cannot address; this step adds top-level alias
# wires for them (graph-verified: cell graph, properties, ports and every original named net unchanged), then runs the
# unchanged ot_rst_copies.tcl splitter (it also splits the reset landing copies).  No gate/threshold relaxation: the
# actual native census must pass on the mapped netlist.
set ot_qcore_copy_max $::env(OT_RST_COPIES_MAX)
unset ::env(OT_RST_COPIES_MAX)
source /src/physical/common_flow/ot_keep_regs.tcl
set ::env(OT_RST_COPIES_MAX) $ot_qcore_copy_max
yosys flatten
yosys techmap
yosys opt_clean
set ot_qcore_alias_dir $::env(RESULTS_DIR)
set ot_qcore_alias_py /src/physical/ref_tile/hbm_su_static_kind2_rg_1020/copy_aliases.py
yosys write_json $ot_qcore_alias_dir/copy_alias_before.json
puts [exec python3 $ot_qcore_alias_py aliases $ot_qcore_alias_dir/copy_alias_before.json $ot_qcore_alias_dir/copy_aliases.ys --top $::env(DESIGN_NAME) --manifest $ot_qcore_alias_dir/copy_aliases.json]
yosys script $ot_qcore_alias_dir/copy_aliases.ys
yosys write_json $ot_qcore_alias_dir/copy_alias_after.json
puts [exec python3 $ot_qcore_alias_py verify $ot_qcore_alias_dir/copy_alias_before.json $ot_qcore_alias_dir/copy_alias_after.json --manifest $ot_qcore_alias_dir/copy_alias_graph.json]
file delete -force $ot_qcore_alias_dir/copy_alias_before.json $ot_qcore_alias_dir/copy_alias_after.json
source /src/physical/common_flow/ot_rst_copies.tcl
