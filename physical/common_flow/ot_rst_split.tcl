# REGIONAL RESET RELAY COPIES (KV-RELAYGEN 2026-10-19; SAFE-DESIGN checklist item 3: a reset relay copy drives <= ~256
# loads).  Sourced by physical/common_flow/ot_keep_regs.tcl (SYNTH_CANONICALIZE_TCL) when OT_RST_SPLIT_MAX is set, AFTER
# the keep attributes are on the register copies.  The RTL already holds N kept, identical relay copies (ot_rst_relay
# REGIONS N from tools/qwen_kv_die/host_cluster/gen_prompt_rr.py or tools/ref_tile/face_land.py; the replicated last
# landing stage of ot_pin_regs.tcl, OT_RST_LAND_COPIES) but each member has one rst_n pin, so copy 0 drove every load.
# Here the design is flattened (the same flatten `synth -flatten` does next; refused for hierarchical / partition
# synthesis) and physical/common_flow/ot_rst_split.py re-points the loads of each copy family over its copies, after
# proving the copies are identical registers.  The table goes to $RESULTS_DIR/ot_rst_split.tsv.
#   OT_RST_SPLIT_MAX  loads a copy (256)          OT_RST_SPLIT_RE  family wire names (default in ot_rst_split.py)
if {[info exists ::env(SYNTH_HIERARCHICAL)] && $::env(SYNTH_HIERARCHICAL) eq "1"} {
  error "OT_RST_SPLIT: needs flat synthesis (SYNTH_HIERARCHICAL=1 would lose its keep_hierarchy choice to the early flatten)"
}
if {[info exists ::env(SYNTH_CHECKPOINT)] && $::env(SYNTH_CHECKPOINT) ne ""} {
  error "OT_RST_SPLIT: not supported with a partition SYNTH_CHECKPOINT"
}
set ot_rs_dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "."}]
set ot_rs_py [file join [file dirname [file normalize [info script]]] ot_rst_split.py]
set ot_rs_args [list --json $ot_rs_dir/ot_rst_split_in.json --max $::env(OT_RST_SPLIT_MAX) \
                  --ys $ot_rs_dir/ot_rst_split.ys --tsv $ot_rs_dir/ot_rst_split.tsv]
if {[info exists ::env(OT_RST_SPLIT_RE)] && $::env(OT_RST_SPLIT_RE) ne ""} { lappend ot_rs_args --re $::env(OT_RST_SPLIT_RE) }
yosys flatten
yosys opt_clean
# multi-bit coarse registers on a relay output would be one indivisible load (a 64-bit $adff = 64 flops on one ARST bit):
# map the registers reset by any relay copy (relay cells by their generated names) to per-bit flops first, as
# ot_keep_regs does for kept registers.  Function unchanged; only the grouping granularity changes.
set ot_rs_rre [expr {[info exists ::env(OT_RST_SPLIT_CELLS)] && $::env(OT_RST_SPLIT_CELLS) ne "" ? $::env(OT_RST_SPLIT_CELLS) : "c:*u_rst_relay* c:*u_fl_rst_* c:*__ot_rl* %u %u"}]
yosys select -set ot_rs_ld {*}$ot_rs_rre {*}{%co2:+[Q,ARST,SRST] t:$adff t:$adffe t:$sdff t:$sdffe t:$sdffce %u %u %u %u %i}
set ot_rs_s [string trim [yosys tee -q -s result.string select -list @ot_rs_ld]]
set ot_rs_n [expr {$ot_rs_s eq "" ? 0 : [llength [split $ot_rs_s "\n"]]}]
puts "OT_RST_SPLIT: $ot_rs_n multi-bit relay-reset register cells mapped to per-bit flops"
yosys techmap @ot_rs_ld
yosys select -clear
yosys write_json $ot_rs_dir/ot_rst_split_in.json
puts [exec python3 $ot_rs_py {*}$ot_rs_args]
yosys script $ot_rs_dir/ot_rst_split.ys
yosys opt_clean
file delete -force $ot_rs_dir/ot_rst_split_in.json
