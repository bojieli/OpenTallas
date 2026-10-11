# MX1 face-leaf source latency re-referenced to THIS session's propagated tree (mtp-mx1 2026-10-10, FT11 sign-off).
#
# fclat.sdc fixes each face leaf's source latency from the calibrate run (placement-RC trees): leaf = CK_<c>_MEAN - local
# leaf insertion.  The routed/SPEF trees are shorter (FT11: core boundary TT 860 -> 643, FF 727 -> 534) while the face
# leaves kept 770 / 656, so at sign-off every face sink sat ~200 ps after the core reference that io_ref_routed.sdc moves
# vclk to (FF hold -224 on every face input, the IO reference and the face capture no longer one die instant).
# The die tree balances the macro's clock pins at the sinks (rule H1: one die instant for every block's nominal
# insertion), so in a session with propagated clocks this file re-derives, in that session's corner and parasitics,
#     source(leaf) = mean core_clk boundary-register insertion - mean local insertion of that leaf's sinks
# exactly as io_ref_routed.sdc re-derives vclk from the routed tree.  Trees stay propagated, no path is cut, no
# uncertainty changes.  Read before signoff_unc60 / vclk_corner_true / io_ref_routed (route_mtp.sh SDCX).  A session
# whose clocks are ideal (synthesis / floorplan SDC reads) is left unchanged.
proc ot_mx1fl_mean {pins} {
  set s 0.0; set n 0
  foreach p $pins {
    set a [get_property $p arrival_max_rise]
    if {[string is double -strict $a]} { set s [expr {$s + $a}]; incr n }
  }
  return [expr {$n ? $s / $n : ""}]
}
set ot_mx1fl_leaves {}
foreach p {cks[0] ckn[0] cke0[0] cke1[0] ckw0[0] ckw1[0]} {
  if {[llength [get_ports -quiet $p]]} {
    foreach c [all_clocks] {
      foreach s [get_property $c sources] { if {[get_full_name $s] eq $p && ![get_property $c is_generated]} { lappend ot_mx1fl_leaves [list $p $c] } }
    }
  }
}
set ot_mx1fl_core [get_clocks -quiet core_clk]
if {[llength $ot_mx1fl_leaves] && [llength $ot_mx1fl_core] && [get_property $ot_mx1fl_core is_propagated]} {
  # core boundary registers: clocked by core_clk and fed by a data input or feeding a data output (io_ref's set)
  set ot_mx1fl_ck {}
  set ot_mx1fl_bnd [dict create]
  set ot_mx1fl_din [all_inputs -no_clocks]
  if {[llength $ot_mx1fl_din]} {
    foreach pe [find_timing_paths -path_delay max -from $ot_mx1fl_din -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {
      dict set ot_mx1fl_bnd [regsub {/[^/]+$} [get_full_name [get_property $pe endpoint]] {}] 1 }
  }
  if {[llength [all_outputs]]} {
    foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {
      dict set ot_mx1fl_bnd [regsub {/[^/]+$} [get_full_name [get_property $pe startpoint]] {}] 1 }
  }
  foreach cp [all_registers -clock $ot_mx1fl_core -clock_pins] {
    if {[dict exists $ot_mx1fl_bnd [regsub {/[^/]+$} [get_full_name $cp] {}]]} { lappend ot_mx1fl_ck $cp }
  }
  if {![llength $ot_mx1fl_ck]} { set ot_mx1fl_ck [all_registers -clock $ot_mx1fl_core -clock_pins] }
  set ot_mx1fl_ref [ot_mx1fl_mean $ot_mx1fl_ck]
  foreach lc $ot_mx1fl_leaves {
    lassign $lc p c
    set_clock_latency -source 0 [get_ports $p]
    set f [ot_mx1fl_mean [all_registers -clock $c -clock_pins]]
    if {$ot_mx1fl_ref eq "" || $f eq ""} { puts "OT_MX1_FCLAT_ROUTED skip $p (no sinks)"; continue }
    set v [expr {$ot_mx1fl_ref - $f}]
    set_clock_latency -source $v [get_ports $p]
    puts [format "OT_MX1_FCLAT_ROUTED %s core-boundary %.1f (n %d) local %.1f -> source %.1f" $p $ot_mx1fl_ref [llength $ot_mx1fl_ck] $f $v]
  }
} else {
  puts "OT_MX1_FCLAT_ROUTED skip (clocks not propagated in this session)"
}
