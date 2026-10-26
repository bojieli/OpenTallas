# PATH-QC-SRAMIF2 post-CTS census (GEOM [PATH-QC-PROG-A1]/[BTAB-A1] 18:45 conditions 1, 3, 4): one corner per run (OT_CORNER),
# 5_1_grt.odb (after the FF-basis GRT hold step), kit SDC + vclk bound, main setRC_rcx_asap7 + GRT parasitics, propagated clocks.
# (1) exhaustive related-pair CPPR census (so_exact/pair_skew.tcl) + the macro-clock class separately: every related pair
#     whose launch or capture is an SRAM macro, exact credited skew per pair (|skew| <= 20 asked), split by IF side (W/E of macro).
# (3) GRT overflow from the 5_1_grt log is read by the caller.  (4) PDN: check_power_grid VDD/VSS.
set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(ODB)
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_sdc /work/constraint.sdc
set bound [expr {$C eq "FF" ? $::env(OT_VCLK_FF) : $::env(OT_VCLK_TT)}]
set vck [lsearch -all -inline -not [all_clocks] [get_clocks clk]]
if {[llength $vck] == 1} { set_clock_latency -source $bound $vck }
source /work/cf/main/setRC_rcx_asap7.tcl
estimate_parasitics -global_routing
set ::ot_ps_lib_only 1
source /work/so_exact/pair_skew.tcl
set_propagated_clock [all_clocks]
ot_ps_zero_unc
set M [ot_ps_measure 5000]
ot_ps_write $M /work/census_pairs_$c.tsv $C
foreach dly {max min} { set m [dict get $M $dly]; puts "CENSUS_ALL $C $dly n [dict get $m n] worst [dict get $m worst] bounded [dict get $m bounded] [dict get $m launch] -> [dict get $m capture]" }
set blk [ord::get_db_block]; set dbu [$blk getDefUnits]
set mac {}
foreach i [$blk getInsts] { if {[[$i getMaster] getType] eq "BLOCK"} { set bb [$i getBBox]; dict set mac [$i getName] [list [expr {[$bb xMin]/double($dbu)}] [expr {[$bb xMax]/double($dbu)}]] } }
lassign [ot_ps_related $::ot_ps_R] P np nx nd
set fh [open /work/census_macro_$c.tsv w]
set W {}
dict for {k v} $P {
  lassign $v l cc dn rs rh
  set lm [dict exists $mac $l]; set cm [dict exists $mac $cc]
  if {!$lm && !$cm} continue
  set m [expr {$cm ? $cc : $l}]; set o [expr {$cm ? $l : $cc}]
  set oi [$blk findInst $o]; set side NA
  if {$oi ne "NULL"} { lassign [dict get $mac $m] x0 x1; set ox [expr {[lindex [$oi getLocation] 0]/double($dbu)}]; set side [expr {$ox < ($x0+$x1)/2.0 ? "W" : "E"}] }
  set cls [expr {$cm ? "to_macro" : "from_macro"}]
  foreach dly {max min} {
    set e [ot_ps_path $l $dn $dly]
    if {![llength $e]} continue
    lassign $e sk cr
    set dmg [expr {$dly eq "max" ? -$sk : $sk}]
    puts $fh "$cls\t$side\t$dly\t$l\t$cc\t[format %.2f $sk]\t[format %.2f $cr]\t[format %.2f $dmg]"
    set key "$cls $side $dly"
    if {![dict exists $W $key]} { dict set W $key [list 0 -1e9 1e9] }
    lassign [dict get $W $key] n mx mn
    dict set W $key [list [incr n] [expr {max($mx,$dmg)}] [expr {min($mn,$dmg)}]]
  }
}
close $fh
dict for {k v} $W { puts "CENSUS_MACRO $C $k n [lindex $v 0] damage max [format %.2f [lindex $v 1]] min [format %.2f [lindex $v 2]]" }
foreach n {VDD VSS} { if {[catch {check_power_grid -net $n} r]} { puts "CENSUS_PDN $C $n ERROR $r" } else { puts "CENSUS_PDN $C $n result $r" } }
puts "CENSUS_DONE $C"
exit
