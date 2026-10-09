# review-0400 R5 (drive-0212): make_sdc.py --period-ps 730 --l-max 813.67 --l-min 650.22 --l-ff-min 519.71 --half --h1 --landing --landing-procs-out cx_landing/headclk_procs.tcl  (= cg/route_h2_cg.sdc + the TUhalf landing clock headclk and the clock-gating checks)
# HA2 banked: period 730.0 ps, L SS 650.22..813.67, FF min 519.71
create_clock -name clk -period 730.000 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ins [delete_from_list [all_inputs] [get_ports clk]]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ins
set_input_delay -max 1160.337 -clock clk $ins
set_input_delay -min 549.710 -clock clk $ins
set_output_delay -max -378.553 -clock clk [all_outputs]
set_output_delay -min -469.710 -clock clk [all_outputs]
set_load 4.0 [all_outputs]
set_false_path -from [get_ports rst_n]
set_max_fanout 32 [current_design]

# half-rate core clock: the ICG AND output is a divide-by-2 generated clock of clk
set ot_g {}
foreach p [get_pins -hierarchical *] {
 set n [get_full_name $p]
 if {[regexp {u_icg.*/Y$} $n]} {
  set c [get_cells -of_objects $p]
  if {[regexp {AND} [get_property $c ref_name]]} {lappend ot_g $p}
 }
}
if {![llength $ot_g]} {error "expected at least one ICG AND output"}
# cg_pushdown (PRE_CTS) clones the gate per sink cluster: gclk is generated at every clone output
create_generated_clock -name gclk -source [get_ports clk] -divide_by 2 $ot_g
# the gclk edge comes from the AND's clock input; en_l changes only while clk is low: no clock through en_l
set ot_q {}
foreach p [get_pins -hierarchical *] { if {[regexp {u_icg.*en_l.*/QN?$} [get_full_name $p]]} {lappend ot_q $p} }
if {[llength $ot_q] && [catch {set_sense -type clock -stop_propagation -clocks [get_clocks clk] $ot_q} ot_e]} {puts "set_sense: $ot_e"}
set_clock_uncertainty -setup 60 [get_clocks gclk]
set_clock_uncertainty -hold 25 [get_clocks gclk]
# ---- TUhalf -cx landing clock (review-0400 R5 / H6(b), drive-0212) ----------------------------------------------
# RTL (ot_ha2_tu_owner_banked_half_cx, LANDING=1, MUT_PHASE=0):
#   ph      : posedge clk toggle
#   gclk    = clk  AND en_l(ph),  en_l latched on negedge clk         -> core clock, rises at the posedge after a ph=1 cycle
#   headclk = !clk AND en_l(!ph), en_l latched on negedge(!clk)=posedge clk -> rises on the clk FALL half a fast cycle
#             before each gclk rise, falls with that gclk rise (pulse width T/2, period 2T)
# Master clk edges: 1 rise 0, 2 fall T/2, 3 rise T, 4 fall 3T/2, 5 rise 2T, 6 fall 5T/2, 7 rise 3T, 8 fall 7T/2.
# gclk (-divide_by 2 above) rises at edges 1, 5, ...  =>  headclk = -edges {4 5 8}: rise at the fall (edge 4) just
# before the gclk rise at edge 5, fall at edge 5, next rise at edge 8.  The rising edge is derived from a FALLING master
# edge through the negative-unate (!clk) leg of the gate, which is what the netlist does.
# Timing this gives (all exact half-cycles, T/2 = 416.7 ps at 833.333): fast FIFO head (clk) -> seat (headclk) setup
# T/2; seat -> core (gclk) setup T/2; seat valid -> fast pop (clk) setup T/2; hold of every crossing >= T/2 of skew.
# The gate output is found by instance (u_head_icg, any cell type) with a net fallback (*headclk / u_head_icg*gclk), so
# the declaration survives naming and a cg_pushdown clone set (ot_ha2_headclk_define is re-run by the PRE_CTS hook).
proc ot_ha2_is_seq {c} { return [regexp {^(DFF|DHL|DLL|SDF|ASYNC_DFF|ICG)} [get_property $c ref_name]] }
# an output pin is a clock-gate output when its net reaches a sequential CLK pin, directly (pre-CTS) or through the
# clock-tree buffers/inverters CTS inserts (sign-off on the routed db)
proc ot_ha2_drives_clk {p} {
  set front [list $p]
  for {set d 0} {$d < 40 && [llength $front]} {incr d} {
    set next {}
    foreach o $front {
      foreach q [get_pins -of_objects [get_nets -of_objects $o]] {
        if {[get_property $q direction] ne "input"} continue
        set c [get_cells -of_objects $q]
        if {[regexp {/CLK$} [get_full_name $q]] && [ot_ha2_is_seq $c]} { return 1 }
        if {[regexp {^(BUF|INV|HB|CKINV|CLKBUF)} [get_property $c ref_name]]} {
          foreach y [get_pins -of_objects $c] { if {[get_property $y direction] eq "output"} { lappend next $y } }
        }
      }
    }
    set front $next
  }
  return 0
}
proc ot_ha2_gate_outs {inst_re net_re} {
  set outs {}
  foreach p [get_pins -hierarchical *] {
    if {![regexp $inst_re [get_full_name $p]]} continue
    if {[get_property $p direction] ne "output"} continue
    if {[ot_ha2_is_seq [get_cells -of_objects $p]]} continue
    if {[ot_ha2_drives_clk $p]} { lappend outs $p }
  }
  if {![llength $outs]} {
    foreach nt [get_nets -hierarchical *] {
      if {![regexp $net_re [get_full_name $nt]]} continue
      foreach p [get_pins -of_objects $nt] {
        if {[get_property $p direction] ne "output"} continue
        if {[ot_ha2_is_seq [get_cells -of_objects $p]]} continue
        if {[ot_ha2_drives_clk $p]} { lappend outs $p }
      }
    }
  }
  return [lsort -unique $outs]
}
proc ot_ha2_headclk_define {} {
  set outs [ot_ha2_gate_outs {u_head_icg[^/]*(/[^/]+)?/[A-Za-z]+[0-9]*$} {(headclk|u_head_icg[./]gclk)$}]
  if {![llength $outs]} { error "OT_HA2_HEADCLK: no head-seat clock gate output (LANDING=0 netlist?)" }
  catch {delete_generated_clock [get_clocks headclk]}
  create_generated_clock -name headclk -source [get_ports clk] -master_clock [get_clocks clk] -edges {4 5 8} $outs
  set_clock_uncertainty -setup 60 [get_clocks headclk]
  set_clock_uncertainty -hold 25 [get_clocks headclk]
  # en_l of the head gate is data (latched while !clk is low): no clock propagation through it
  set q {}
  foreach p [get_pins -hierarchical *] { if {[regexp {u_head_icg.*en_l.*/QN?$} [get_full_name $p]]} {lappend q $p} }
  if {[llength $q] && [catch {set_sense -type clock -stop_propagation -clocks [get_clocks clk] $q} e]} {puts "OT_HA2_HEADCLK: set_sense: $e"}
  # clock-gating checks on both gates (active-high AND gating: the enable must be stable while the gate's clock input
  # is high): u_icg (gclk) and u_head_icg (headclk).  Margins are added to the propagated-clock check.
  foreach g [concat [ot_ha2_gate_outs {u_icg[^/]*(/[^/]+)?/[A-Za-z]+[0-9]*$} {u_icg[./]gclk$}] $outs] {
    set c [get_cells -of_objects $g]
    if {[catch {set_clock_gating_check -high -setup 25 -hold 25 $c} e]} {puts "OT_HA2_HEADCLK: gating check: $e"}
  }
  puts "OT_HA2_HEADCLK: headclk on [llength $outs] gate output(s) (-edges 4 5 8 of clk); clk stopped at [llength $q] en_l output(s)"
}
ot_ha2_headclk_define
