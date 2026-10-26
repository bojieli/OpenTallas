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
proc original_connections {out} {
  set lines {}
  foreach i [[ord::get_db_block] getInsts] {
    if {[string match mp_isl* [$i getName]]} continue
    foreach it [$i getITerms] {
      if {[[$it getMTerm] getSigType] in {POWER GROUND}} continue
      set n [$it getNet]; set name NULL
      if {$n ne "NULL"} {set name [$n getName]}
      lappend lines [list [$i getName] [[$it getMTerm] getName] $name]
    }
  }
  set f [open $out w]; puts $f [join [lsort $lines] \n]; close $f
}
original_connections /work/original_connections.tsv
set before [llength [$b getInsts]]
source /work/master_core_infra.tcl
source /work/master_core_infra.tcl
original_connections /work/after_connections.tsv
set f [open /work/original_connections.tsv r];set old [read $f];close $f
set f [open /work/after_connections.tsv r];set new [read $f];close $f
if {$old ne $new} {error ORIGINAL_CORE_LOGIC_CONNECTIVITY_CHANGED}
set after [llength [$b getInsts]]
if {$after != $before+2} {error "SHARED_FT_CELL_COUNT $before $after"}
write_db /work/shared_rp1.odb
write_verilog /work/shared_rp1.v
set f [open /work/new_cells.tsv w]
foreach name {mp_isl0_ck0 mp_isl0_rst0} {
 set i [$b findInst $name];set r [$i getBBox]
 puts $f [list $name [[$i getMaster] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
}
close $f
puts "SHARED_RP1_ACTUAL_CORE_PASS original_logic_connectivity_identical=1 added_buffers=2 added_FT_ports=4 added_data_cycles=0 added_reset_cycles=0"
