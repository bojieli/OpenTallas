# Opt-in preservation of explicitly enumerated ORIGINAL constant-D captures.
# Called after the normal keep hook has split and marked per-bit FFs, before opt.
set ot_cff_dir [file dirname [file normalize [info script]]]
set ot_cff_base [file join $::env(RESULTS_DIR) ot_const_dff]
if {![file isfile $::env(OT_CONST_DFF_SPEC)]} {error "OT_CONST_DFF_SPEC is not a file"}
yosys write_json ${ot_cff_base}.before.json
puts [exec python3 [file join $ot_cff_dir const_dff_keep.py] prepare ${ot_cff_base}.before.json $::env(OT_CONST_DFF_SPEC) --tcl ${ot_cff_base}.select.tcl --receipt ${ot_cff_base}.receipt.json]
set ot_cff_lib [string trim [yosys tee -q -s result.string select -list m:DFFHQNx2_ASAP7_75t_R]]
if {$ot_cff_lib eq ""} {yosys read_verilog -lib [file join $ot_cff_dir ot_const_dff_bb.v]}
source ${ot_cff_base}.select.tcl
yosys techmap -map [file join $ot_cff_dir ot_const_dff_map.v] @ot_const_dff_keep
# Fold only combinational constant expressions introduced by the polarity map.
yosys opt_expr
yosys write_json ${ot_cff_base}.mapped.json
puts [exec python3 [file join $ot_cff_dir const_dff_keep.py] verify ${ot_cff_base}.mapped.json ${ot_cff_base}.receipt.json]
