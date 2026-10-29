source /probe/libsel.tcl
foreach f [ot_lib_resolve TT] {read_liberty $f}
read_db /work/run/results/asap7/kl_ot_v41_bf_col_codex_icg_g2/base/3_5_place_dp.odb
read_sdc /work/constraint.sdc
source /work/clock_family.tcl
set fo [open /probe/out/probe.txt w]
set icg [get_pins mp_ck_T00003_icg/CLK]
sta::redirect_string_begin; report_edges -from $icg; set r [sta::redirect_string_end]
puts $fo "EDGES_FROM_ICG_CLK:\n$r"
set regs [all_registers -clock_pins]
set nicg 0; foreach p $regs { if {[string match ICG* [get_property [get_cells -of_objects $p] ref_name]]} {incr nicg} }
puts $fo "ALL_REGISTERS_CLOCK_PINS [llength $regs] of_which_ICG $nicg"
# walk like tap_balance.tb_sinks, original vs ICG-through
proc walk {net thru} {
  set out {}; set icgs 0; set todo [list $net]; set seen {}
  while {[llength $todo]} {
    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {[dict exists $seen [$n getName]]} continue
    dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set i [$it getInst]; set m [[$i getMaster] getName]
      set isb [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m] || [string match "HB*" $m]}]
      if {$thru && [string match "ICG*" $m] && [[$it getMTerm] getName] eq "CLK"} {set isb 1; incr icgs}
      if {$isb} {
        foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
      } else { lappend out "[$i getName]/[[$it getMTerm] getName]" }
    }
  }
  return [list $out $icgs]
}
set net [[[ord::get_db_block] findBTerm clk] getNet]
foreach thru {0 1} {
  lassign [walk $net $thru] s icgs
  set nI 0; set masters {}
  foreach p $s { set m [[[[ord::get_db_block] findInst [regsub {/[^/]+$} $p {}]] getMaster] getName]; dict incr masters [regsub {_ASAP7.*} $m {}]; if {[string match ICG* $m]} {incr nI} }
  puts $fo "WALK thru_icg=$thru sinks [llength $s] icg_sinks $nI icgs_traversed $icgs masters $masters"
}
set_propagated_clock [all_clocks]
estimate_parasitics -placement
ot_cf_refresh
lassign [walk $net 1] s icgs
set bad 0; set ok 0; set amin 1e9; set amax 0
foreach p [lrange $s 0 1999] { set pin [get_pins $p]; if {[catch {set a [ot_cf_wire $pin [lindex [get_property $pin clocks] 0]]} e]} {incr bad; if {$bad<4} {puts $fo "ERR $p $e"}} else {incr ok; set amin [expr {min($amin,$a)}]; set amax [expr {max($amax,$a)}]} }
puts $fo "OT_CF_WIRE thru_icg first2000 ok $ok err $bad min $amin max $amax (placement RC, pre-CTS ideal tree: INFO only)"
close $fo
