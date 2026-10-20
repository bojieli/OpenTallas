# Own source prototype only: keep source copies, bit-map logic, then invoke unchanged exact-copy proof/splitter.
# This performs no gate or threshold relaxation. Actual native census must pass after ABC.
set ot_qcore_copy_max $::env(OT_RST_COPIES_MAX)
unset ::env(OT_RST_COPIES_MAX)
source /src/physical/common_flow/ot_keep_regs.tcl
set ::env(OT_RST_COPIES_MAX) $ot_qcore_copy_max
yosys flatten
yosys techmap
yosys opt_clean
set ot_qcore_alias_dir $::env(RESULTS_DIR)
yosys write_json $ot_qcore_alias_dir/copy_alias_before.json
puts [exec python3 /src/results/arch/hbm_qcore7_native32_1020/copy_aliases.py aliases $ot_qcore_alias_dir/copy_alias_before.json $ot_qcore_alias_dir/copy_aliases.ys --top $::env(DESIGN_NAME) --manifest $ot_qcore_alias_dir/copy_aliases.json]
yosys script $ot_qcore_alias_dir/copy_aliases.ys
yosys write_json $ot_qcore_alias_dir/copy_alias_after.json
puts [exec python3 /src/results/arch/hbm_qcore7_native32_1020/copy_aliases.py verify $ot_qcore_alias_dir/copy_alias_before.json $ot_qcore_alias_dir/copy_alias_after.json --manifest $ot_qcore_alias_dir/copy_alias_graph.json]
source /src/physical/common_flow/ot_rst_copies.tcl
