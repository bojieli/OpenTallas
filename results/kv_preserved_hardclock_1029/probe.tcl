read_liberty /work/macros/ot_qkh_recip_leaf_tt.lib
read_db /work/run/results/asap7/hc_qkd_ahub__604_8x440_64/base/3_place.odb
source /probe/core_infra.tcl
ot_ci_begin
ot_ci_tree_begin {ck[0]}
set bt [$::ot_ci_b findBTerm {ck[0]}]
set original [$bt getNet]
puts "ACTUAL_ORIGINAL_ROOT_SINKS [llength $::ot_ci_tree_expected]"
set macro {}
foreach it $::ot_ci_tree_expected {if {[[$it getInst] getMaster] ne "NULL" && [[[ $it getInst] getMaster] isBlock]} {set macro $it}}
if {$macro eq ""} {error NO_ACTUAL_MACRO}
set name [[ $macro getInst] getName];set pin [[ $macro getMTerm] getName]
ot_ci_tree_preserve_hard {ck[0]} $name/$pin ot_qkh_recip_leaf
if {[$macro getNet] ne $original || [llength $::ot_ci_tree_seen] != 1} {error PRESERVED_ROOT_CHANGED}
puts "ACTUAL_PRESERVE_PASS $name/$pin [llength $::ot_ci_tree_expected] sinks, [llength $::ot_ci_tree_seen] explicitly_preserved, rest_remain_required"
if {![catch {ot_ci_tree_finish} msg] || ![string match *UNASSIGNED_CLOCK_SINK* $msg]} {error MISSING_FF_CENSUS_WAIVED}
puts "ACTUAL_UNASSIGNED_FF_CONTROL_CAUGHT $msg"
