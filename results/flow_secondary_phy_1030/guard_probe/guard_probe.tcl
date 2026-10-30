read_db /input/run/results/asap7/dp_kv3_sys_SD/base/3_4_place_resized.odb
set blk [ord::get_db_block]
set roots {}
foreach bt [$blk getBTerms] {
 set n [$bt getName]
 if {[$bt getIoType] eq "INPUT" && ([string match {clk*} $n] || [string match {fclk_i*} $n] || [string match {ft_ck_i*} $n])} {lappend roots $n}
}
puts "PROBE_ROOTS [lsort $roots]"
set ::ot_ci_scope_roots [lsort $roots]
set ::ot_ci_scope_owned {clk_clk_phy[0]}
set ::ot_ci_scope_editors {}
set ::ot_ci_scope_known {}
source /work/core_infra_scope.tcl
set tick [clock milliseconds]
set cones [ot_ci_scope_disjoint]
dict for {root info} $cones {puts "PROBE_CONE $root nets=[llength [dict get $info nets]] records=[llength [dict get $info graph]]"}
set before [ot_ci_scope_snapshot [list $::ot_ci_scope_owned]]
if {[ot_ci_scope_snapshot [list $::ot_ci_scope_owned]] ne $before} {error SNAPSHOT_UNSTABLE}
puts "PROBE_PASS stable=1 roots=[llength $roots] elapsed_ms=[expr {[clock milliseconds]-$tick}]"
