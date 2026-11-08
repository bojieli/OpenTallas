# DIE-HBM-92-OPEN/VECD vXLK form (2026-11-08): CLOCK CROSS-ROOT lockups, safe by construction.
# Measured (vK0 routed FF probe): 2481/2481 non-port hold violators are register hops between the native
# clk tree and the four face trees clk_n/clk_s/clk_e/clk_w (u_bin->x__ot_q, x__ot_q->bank.*_d,
# bank.rr/pr_d/eg_d/status/done->u_bout); 8 independent CTS roots, insertion 309-386 ps, so a zero-logic hop
# between two roots pays the root-to-root spread.  Form: every capture register on one of those five roots whose
# WHOLE data fan-in launches on exactly ONE other of those roots gets one transparent-low DLLx1 lockup at its D,
# clocked by the launch root.  The latch passes data only in the launch clock low phase: hold margin ~T/2 minus
# skew by construction, setup keeps T/2.  Cycle-exact (LEC latch_to_wire), PIN CYCLES 0.  All 8 native clock
# ports keep their sinks (latches join the launch trees).  Macro-root (clk_macro*) launches, port launches and
# mixed-root fan-ins are untouched.
set xlk_roots {clk clk_n clk_s clk_e clk_w}
set xlk_master [[ord::get_db] findMaster DLLx1_ASAP7_75t_R]
if {$xlk_master eq "NULL" || $xlk_master eq ""} {error "VECD_XLK DLLx1 master absent"}
set xlk_blk [ord::get_db_block]
set xlk_t {}
set xlk_skip [dict create]
foreach ck [all_registers -edge_triggered -clock_pins] {
  set cell [get_cells -of_objects $ck]
  set cnet [get_full_name [get_nets -of_objects $ck]]
  if {$cnet ni $xlk_roots} {dict incr xlk_skip capture_root_other; continue}
  set d [get_pins -quiet [get_full_name $cell]/D]
  if {![llength $d]} {dict incr xlk_skip no_d; continue}
  set src {}; set bad ""
  foreach s [get_fanin -to $d -startpoints_only -flat] {
    set sn [get_full_name $s]
    if {[llength [get_ports -quiet $sn]]} {set bad port; break}
    if {![regexp {/CLK$} $sn]} {set bad nonreg; break}
    lappend src [get_full_name [get_nets -of_objects $s]]
  }
  set src [lsort -unique $src]
  if {$bad ne ""} {dict incr xlk_skip $bad; continue}
  if {[llength $src] != 1} {dict incr xlk_skip [expr {[llength $src] ? "mixed" : "nofanin"}]; continue}
  set l [lindex $src 0]
  if {$l eq $cnet} {dict incr xlk_skip same; continue}
  if {$l ni $xlk_roots} {dict incr xlk_skip macro_launch; continue}
  lappend xlk_t [list [sta::sta_to_db_inst $cell] $l $cnet]
}
set xlk_f [open $::env(RESULTS_DIR)/vecd_xlk.tsv w]
set xlk_n 0; set xlk_pairs [dict create]
foreach t $xlk_t {
  lassign $t di l c
  set dp [$di findITerm D]
  set lnet [$xlk_blk findNet $l]
  if {$dp eq "NULL" || $lnet eq "NULL"} {error "VECD_XLK missing D or launch net [$di getName] $l"}
  set old [$dp getNet]
  set ni [odb::dbInst_create $xlk_blk $xlk_master "vecd_xlk_$xlk_n"]
  set nn [odb::dbNet_create $xlk_blk "vecd_xlk_${xlk_n}_q"]
  $dp disconnect; $dp connect $nn
  [$ni findITerm D] connect $old
  [$ni findITerm Q] connect $nn
  [$ni findITerm CLK] connect $lnet
  puts $xlk_f "vecd_xlk_$xlk_n\t[$di getName]\t$l\t$c"
  dict incr xlk_pairs "$l->$c"
  incr xlk_n
}
close $xlk_f
global_connect
puts "VECD_XLK lockups $xlk_n pairs [dict get $xlk_pairs] skipped $xlk_skip PIN_CYCLES 0"
if {$xlk_n < 1000} {error "VECD_XLK unexpectedly few lockups $xlk_n"}
