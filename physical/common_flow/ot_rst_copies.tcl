# REGIONAL RESET RELAY COPIES (KV-RELAYGEN 2026-10-19; SAFE-DESIGN checklist item 3: a reset relay copy drives <= ~256
# loads).  Sourced by physical/common_flow/ot_keep_regs.tcl (SYNTH_CANONICALIZE_TCL) when OT_RST_COPIES_MAX is set, AFTER
# the keep attributes are on the register copies.  The RTL already holds N kept, identical relay copies (ot_rst_relay
# REGIONS N from tools/qwen_kv_die/host_cluster/gen_prompt_rr.py or tools/ref_tile/face_land.py; the replicated last
# landing stage of ot_pin_regs.tcl, OT_RST_LAND_COPIES) but each member has one rst_n pin, so copy 0 drove every load.
# Here the design is flattened (the same flatten `synth -flatten` does next; refused for hierarchical / partition
# synthesis) and physical/common_flow/ot_rst_copies.py re-points the loads of each copy family over its copies, after
# proving the copies are identical registers.  The table goes to $RESULTS_DIR/ot_rst_copies.tsv.
#   OT_RST_COPIES_MAX  loads a copy (256)          OT_RST_COPIES_RE  family wire names (default in ot_rst_copies.py)
if {[info exists ::env(SYNTH_HIERARCHICAL)] && $::env(SYNTH_HIERARCHICAL) eq "1"} {
  error "OT_RST_COPIES: needs flat synthesis (SYNTH_HIERARCHICAL=1 would lose its keep_hierarchy choice to the early flatten)"
}
if {[info exists ::env(SYNTH_CHECKPOINT)] && $::env(SYNTH_CHECKPOINT) ne ""} {
  error "OT_RST_COPIES: not supported with a partition SYNTH_CHECKPOINT"
}
set ot_rs_dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : "."}]
set ot_rs_py [file join [file dirname [file normalize [info script]]] ot_rst_copies.py]
set ot_rs_args [list --json $ot_rs_dir/ot_rst_copies_in.json --max $::env(OT_RST_COPIES_MAX) \
                  --ys $ot_rs_dir/ot_rst_copies.ys --tsv $ot_rs_dir/ot_rst_copies.tsv]
set ot_rs_re [expr {[info exists ::env(OT_RST_COPIES_RE)] && $::env(OT_RST_COPIES_RE) ne "" ? [list --re $::env(OT_RST_COPIES_RE)] : {}}]
lappend ot_rs_args {*}$ot_rs_re
# KV-PC SAFE 10-19 (opt-in): OT_RST_COPIES_WIDE=1 -> the prep also maps family-read memories / coarse cells per gate
set ot_rs_wide [expr {[info exists ::env(OT_RST_COPIES_WIDE)] && $::env(OT_RST_COPIES_WIDE) eq "1" ? [list --wide] : {}}]
yosys flatten
yosys opt_clean
# KV-PC SAFE 10-19 (OT_RST_COPIES_WIDE=1 only): fold hold-feedback muxes into enables first, so N identical copies of a
# register that HOLDS its value (D = mux(Q_own, next, en) after proc) become identical $dffe cells (D = next, EN = en);
# otherwise every copy's D differs by its own Q and the identity proof refuses the family.  synth runs opt_dff anyway.
if {$ot_rs_wide ne {}} { yosys opt_dff }
# multi-bit coarse registers on a relay copy would be one indivisible load (a 64-bit $adff = 64 flops on one ARST bit):
# ot_rst_copies.py --prep lists them and they are mapped to per-bit flops first (as ot_keep_regs does for kept
# registers).  Function unchanged; only the grouping granularity changes.
yosys write_json $ot_rs_dir/ot_rst_copies_in.json
puts [exec python3 $ot_rs_py --prep --json $ot_rs_dir/ot_rst_copies_in.json --ys $ot_rs_dir/ot_rst_copies_prep.ys {*}$ot_rs_re {*}$ot_rs_wide]
yosys script $ot_rs_dir/ot_rst_copies_prep.ys
yosys opt_clean
yosys write_json $ot_rs_dir/ot_rst_copies_in.json
puts [exec python3 $ot_rs_py {*}$ot_rs_args]
yosys script $ot_rs_dir/ot_rst_copies.ys
yosys opt_clean
file delete -force $ot_rs_dir/ot_rst_copies_in.json
