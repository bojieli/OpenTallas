# CORES-KITS/KVX t1 post-CTS clock check (read-only): per-corner propagated CK arrivals per tap group + face pin regs,
# macro-vs-reg table, related-pair skew with CPPR (pair_skew.tcl), placement RC (setRC_rcx), FF vclk bound 202.5.
# env: OT_CORNER tt|ff, OT_LIBS, OUTD
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l $::env(OT_LIBS) { read_liberty $l }
set R [glob /work/run/results/asap7/*/base]
read_db $R/4_cts.odb
read_sdc $R/4_cts.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set c $::env(OT_CORNER)
if {$c eq "ff"} { set ::env(OT_VCLK_CORNER) ff; source /work/vclk_corner.tcl }
set ::ot_ps_lib_only 1
source /work/pair_skew.tcl
set ::ot_ps_method tag
source /work/pv_pair_taps_key.tcl
set clk [get_clocks clk]
set face {}
set ff [open $R/ot_face_flops.txt r]; foreach l [split [read $ff] \n] { set w [lindex [split $l \t] 0]; if {$w ne ""} { lappend face $w } }; close $ff
array set isface {}
foreach f $face { set isface([string map {\\ {}} $f]) 1 }
set out [open $::env(OUTD)/taps_$c.tsv w]
puts $out "group\tkind\tn\tmean\tmin\tmax"
# force the arrival search first (ot_ps_ckarr reads path tags; none exist before a timing update)
report_worst_slack -max > /dev/null
report_worst_slack -min > /dev/null
array set acc {}
foreach inst [get_cells -hierarchical *] {
  set m [get_property $inst ref_name]
  set nm [get_full_name $inst]
  if {[regexp {^ot_sram} $m]} { set kind macro } elseif {[regexp {^(DFF|ASYNC|SDF|DHL|DLL)} $m]} { set kind reg } else continue
  set pin ""
  foreach p [get_pins -of_objects $inst] { if {[regexp {^(CLK|clk)$} [get_property $p lib_pin_name]]} { set pin $p; break } }
  if {$pin eq ""} continue
  set a [ot_ps_ckarr $pin $clk max]
  if {$a eq ""} continue
  set g [ot_pv_key $nm]
  set n2 [string map {\\ {}} $nm]
  foreach key [list "$g\t$kind" [expr {[info exists isface($n2)] ? "FACE\tpinreg" : "ALL\t$kind"}] "ALL\tall_$kind"] {
    if {![info exists acc($key)]} { set acc($key) [list 0 0.0 1e9 -1e9] }
    lassign $acc($key) n s lo hi
    set acc($key) [list [incr n] [expr {$s + $a}] [expr {min($lo,$a)}] [expr {max($hi,$a)}]]
  }
}
foreach key [lsort [array names acc]] { lassign $acc($key) n s lo hi; puts $out [format "%s\t%d\t%.1f\t%.1f\t%.1f" $key $n [expr {$s/$n}] $lo $hi] }
close $out
puts "OT_POSTCTS taps written $c"
report_checks -path_delay max -group_path_count 1 -sort_by_slack -format full_clock_expanded > $::env(OUTD)/sta_${c}_max.rpt
report_checks -path_delay min -group_path_count 1 -sort_by_slack -format full_clock_expanded > $::env(OUTD)/sta_${c}_min.rpt
puts "OT_POSTCTS wns [sta::worst_slack_cmd max] whs [sta::worst_slack_cmd min]"
if {[info exists ::env(OT_SKIP_PS)]} { puts "OT_POSTCTS done $c (no ps)"; exit }
set ::env(OT_PS_OUT) $::env(OUTD)/pair_skew_$c.tsv
set ::env(CORNER) $c
ot_ps_main
puts "OT_POSTCTS done $c"
