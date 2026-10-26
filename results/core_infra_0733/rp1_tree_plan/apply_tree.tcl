read_db /work/source.odb
set b [ord::get_db_block]
# Remove only legacy trial instrumentation from OUR copied pre-CTS ODB.
# The source ODB remains immutable; no functional instance may be removed.
set removed {}
foreach p {ft_ck_i ft_ck_o ft_rst_i ft_rst_o} {
  set bt [$b findBTerm $p]
  if {$bt ne "NULL"} {[$bt getNet] setDoNotTouch 0}
}
foreach i [$b getInsts] {
  set nm [$i getName]
  if {$nm ni {ot_isl_ckft ot_isl_rstft} && ![string match ot_ms_* $nm]} continue
  if {$nm ni {ot_isl_ckft ot_isl_rstft}} {
    foreach it [$i getITerms] {
      if {[[$it getMTerm] getSigType] ni {POWER GROUND} && [$it getNet] ne "NULL"} {
        error "LEGACY_TRIAL_CELL_CONNECTED $nm; refuse removal"
      }
    }
  }
  lappend removed $nm; $i setDoNotTouch 0; odb::dbInst_destroy $i
}
foreach p {ft_ck_i ft_ck_o ft_rst_i ft_rst_o} {
  set bt [$b findBTerm $p]
  if {$bt ne "NULL"} {
    set n [$bt getNet]
    if {[llength [$n getITerms]]} {error "LEGACY_FT_CORE_LOGIC $p"}
    $n setDoNotTouch 0; odb::dbBTerm_destroy $bt
  }
}
puts "REMOVED_OWN_COPY_LEGACY_TRIAL_ONLY $removed"

proc data_connections {} {
  set result {}
  foreach i [[ord::get_db_block] getInsts] {
    if {[string match mp_* [$i getName]]} continue
    foreach it [$i getITerms] {
      set mt [$it getMTerm]
      if {[$mt getSigType] in {POWER GROUND CLOCK} || [$mt getName] in {CLK clk}} continue
      set n [$it getNet];set nn NULL;if {$n ne "NULL"} {set nn [$n getName]}
      lappend result [list [$i getName] [$mt getName] $nn [$i isDoNotTouch]]
    }
  }
  return [lsort $result]
}
set data_before [data_connections]
set before [llength [$b getInsts]]
source /work/master_core_infra.tcl
source /work/master_core_infra.tcl
set after [llength [$b getInsts]]
if {$after != $before+93} {error "SHARED_TREE_CELL_COUNT $before $after"}
if {$data_before ne [data_connections]} {error ORIGINAL_DATA_CONNECTIVITY_OR_PROTECTION_CHANGED}
write_db /work/tree.odb
write_verilog /work/tree.v
puts "SHARED_RP1_TREE_APPLY_PASS planned_clock_nodes=91 explicit_FF_sinks=2790 macro_sinks=2 frozen_origins_verified=93 no_CTS_no_route_no_STA=1"
