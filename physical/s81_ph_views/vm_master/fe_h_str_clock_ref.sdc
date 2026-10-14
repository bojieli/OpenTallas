# el1013-s81-vmfe/B6: the two clocks of dsfd_vm_fcc / dsfd_vm_fcn at their TRUE periods for the REFERENCE TILE FLOW
# (spec sdc_extra: inlined at the end of clock.sdc and signoff.sdc; re-read after every io_ref switch by
# fe_h_str_boundary.tcl).  One die PLL, ratio 4 : 3:
#   str_clk = cks, the stream clock    = the period ref_tile generated for core_clk (route 770 ps, sign-off 833.333 ps)
#   core_clk = ck, the VM serial clock = 4/3 of it                                  (route 1,026.667, sign-off 1,111.111)
# B5's version kept ck at 833.333 and put cks at 3/4 of it (625 ps): 33 % stricter than the design in both domains and in
# the crossing window (208 instead of 278 ps); its -308 ps (fcn dv / dt) and -27 ps (fcc u_cc1.wp_r) were measured there.
# The ratio-CDC crossings (ot_ratio_cdc_fifo flop -> flop) and the engine adapter's FIFO crossings stay TIMED between the
# two related clocks (no clock groups, no false path): window 277.8 ps at sign-off.
# Boundary, both domains, the io_ref_skew.sdc form re-referenced to each clock's OWN propagated tree:
#   in  max = E + L_max + 90   min = L_min          out max = E - L_max + 90   min = -L_min - 50
#   L = clock arrival of the domain's boundary register of median arrival (0 while the clocks are ideal)
#   E = period - (base - 166.667): every pin keeps the budget of an 833.333-ps leaf (pin -> flop / flop -> pin within
#       0.8 x 833.333), in the stream domain (E = 166.667 = 0.2 T) and in the serial domain alike (E = 444.444: the
#       neighbours of these pins are leaves signed off at 833.333, so the longer serial period is NOT given to the pins)
set ot_fh_core [get_clocks core_clk]
set ot_fh_cp [get_property $ot_fh_core period]
set ot_fh_str [get_clocks -quiet str_clk]
if {[llength $ot_fh_str] && abs($ot_fh_cp - [get_property $ot_fh_str period] * 4.0 / 3.0) < 0.01} {
  set ot_fh_base [get_property $ot_fh_str period]         ;# already applied (in-flow re-read): keep the clocks
} else {
  set ot_fh_base $ot_fh_cp                                ;# fresh clock.sdc / signoff.sdc: core_clk was just created at the base
  set ot_fh_prop 0
  catch {set ot_fh_prop [get_property $ot_fh_core is_propagated]}
  create_clock -name str_clk -period $ot_fh_base [get_ports {cks}]
  create_clock -name core_clk -period [expr {$ot_fh_base * 4.0 / 3.0}] [get_ports {ck}]
  if {$ot_fh_prop} { set_propagated_clock [all_clocks] }
  set_clock_uncertainty -setup 60 [all_clocks]
  set_clock_uncertainty -hold 25 [all_clocks]
}
set ot_fh_cp [get_property [get_clocks core_clk] period]
proc ot_fh_ref {globs} {
  # {L_max L_min} of the median-arrival CLK pin over the cells matching the globs; {0 0} while the clock is ideal
  catch {sta::worst_slack_cmd max}
  set pf {}
  foreach g $globs {
    foreach c [get_cells -quiet -hierarchical $g] {
      set p [get_pins -quiet "[get_full_name $c]/CLK"]
      if {![llength $p]} { continue }
      set a [get_property $p arrival_max_rise]; set b [get_property $p arrival_min_rise]
      if {[string is double -strict $a] && [string is double -strict $b] && abs($a) < 1e6 && abs($b) < 1e6} { lappend pf [list $a $b] }
    }
  }
  if {![llength $pf]} { return {0.0 0.0 0} }
  set pf [lsort -real -index 0 $pf]
  set m [lindex $pf [expr {[llength $pf] / 2}]]
  return [list [lindex $m 0] [lindex $m 1] [llength $pf]]
}
# stream-domain ports (fcc: the ctrl VM request; fcn: the engine channel); everything else is serial
set ot_fh_si [get_ports -quiet {vwe vwa[*] vwd[*] vre vra[*] cv cd[*] vwe[*] vre[*] cv[*]}]
set ot_fh_so [get_ports -quiet {dv dt[*] dv[*]}]
set ot_fh_sn {}
foreach p [concat $ot_fh_si $ot_fh_so] { lappend ot_fh_sn [get_full_name $p] }
set ot_fh_ci {}; set ot_fh_co {}
foreach p [all_inputs -no_clocks] { if {[lsearch -exact $ot_fh_sn [get_full_name $p]] < 0} { lappend ot_fh_ci $p } }
foreach p [all_outputs] { if {[lsearch -exact $ot_fh_sn [get_full_name $p]] < 0} { lappend ot_fh_co $p } }
catch {unset_input_delay [all_inputs]}
catch {unset_output_delay [all_outputs]}
lassign [ot_fh_ref {*u_s0*}] ot_fh_cx ot_fh_cn ot_fh_cc
lassign [ot_fh_ref {cd_p* dt_q* s_wd*}] ot_fh_sx ot_fh_sm ot_fh_sc
set ot_fh_ce [expr {$ot_fh_cp - ($ot_fh_base - 166.667)}]
set ot_fh_se 166.667
puts [format "FE_H two-clock boundary: base %.3f core_clk %.3f str_clk %.3f | serial E %.3f L %.1f / %.1f (%d out flops) | stream E %.3f L %.1f / %.1f (%d pin flops) | ports serial %d in %d out, stream %d in %d out" \
  $ot_fh_base $ot_fh_cp $ot_fh_base $ot_fh_ce $ot_fh_cx $ot_fh_cn $ot_fh_cc $ot_fh_se $ot_fh_sx $ot_fh_sm $ot_fh_sc \
  [llength $ot_fh_ci] [llength $ot_fh_co] [llength $ot_fh_si] [llength $ot_fh_so]]
if {[llength $ot_fh_ci]} {
  set_input_delay [expr {$ot_fh_ce + $ot_fh_cx + 90}] -max -clock core_clk $ot_fh_ci
  set_input_delay [expr {$ot_fh_cn}] -min -clock core_clk $ot_fh_ci
}
if {[llength $ot_fh_co]} {
  set_output_delay [expr {$ot_fh_ce - $ot_fh_cx + 90}] -max -clock core_clk $ot_fh_co
  set_output_delay [expr {0 - $ot_fh_cn - 50}] -min -clock core_clk $ot_fh_co
}
if {[llength $ot_fh_si]} {
  set_input_delay [expr {$ot_fh_se + $ot_fh_sx + 90}] -max -clock str_clk $ot_fh_si
  set_input_delay [expr {$ot_fh_sm}] -min -clock str_clk $ot_fh_si
}
if {[llength $ot_fh_so]} {
  set_output_delay [expr {$ot_fh_se - $ot_fh_sx + 90}] -max -clock str_clk $ot_fh_so
  set_output_delay [expr {0 - $ot_fh_sm - 50}] -min -clock str_clk $ot_fh_so
}
# asynchronous resets enter through synchronisers
set_false_path -from [get_ports -quiet {rst rss rst[*] rss[*]}]
