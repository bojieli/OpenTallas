# rck_tree_dump.tcl (RCK-REBALANCE-1, FABLE-FIX-S81-SERDES2 2026-11-18): dump one clock tree with EXTRACTED sink arrivals.
# Input of rck_rebalance.py.  Read-only.  Run in OpenROAD with the routed DB, the kit SDC and the SPEF already loaded (or let it
# load them: env RTD_ODB, RTD_SDC, RTD_LIBS = space list, RTD_SPEF; without RTD_SPEF the global-route estimate is used), propagated
# clocks.  S lines carry the late (max) arrival and, as a 5th column, the early (min) arrival of the same edge.
#   env RTD_PORT  clock source port (default io_pma_rck[0]);  RTD_OUT  output TSV
# Lines:  K <parent> <child>          tree edge between clock cells (root = PORT), BUF/INV/CKINV/HB cells as in subtree_balance.tcl
#         S <node> <sink pin> <arrival ps>   register / macro clock pin below <node>; arrival of the SAME source edge (an odd number
#                                            of inverters above the pin -> its fall arrival), so every sink reads insertion delay
#         X <node> <x> <y>            cell location (dbu), for the insert step
proc rtd_env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }
if {[rtd_env RTD_ODB ""] ne ""} {
  foreach l [rtd_env RTD_LIBS ""] { read_liberty $l }
  read_db $::env(RTD_ODB); read_sdc $::env(RTD_SDC)
  if {[rtd_env RTD_RC ""] ne ""} { source $::env(RTD_RC) }
  if {[rtd_env RTD_SPEF ""] ne ""} { read_spef $::env(RTD_SPEF) } else { estimate_parasitics -global_routing }
}
set_propagated_clock [all_clocks]
# build the timing graph and the arrivals first: get_property <pin> arrival_* on a fresh session dereferences a graph that
# does not exist yet (OpenSTA Graph::pinVertices, signal 11)
puts "OT_RCK_TREE_DUMP wns_max [format %.2f [sta::worst_slack -max]]"
set ::env(OT_STB) 0
source [file join [file dirname [file normalize [info script]]] subtree_balance.tcl]
set rtd_p [rtd_env RTD_PORT {io_pma_rck[0]}]
lassign [stb::build $rtd_p] rtd_nn rtd_ns
set rtd_f [open [rtd_env RTD_OUT rck_tree.tsv] w]
set rtd_blk [ord::get_db_block]; set rtd_na 0
set rtd_pre "$rtd_p,"; set rtd_pl [string length $rtd_pre]
foreach rtd_k [array names ::stb::kids] {
  # exact prefix compare: a bus port name (io_pma_rck[0]) is not a glob pattern
  if {[string range $rtd_k 0 [expr {$rtd_pl - 1}]] ne $rtd_pre} continue
  set rtd_n [string range $rtd_k $rtd_pl end]
  foreach rtd_c $::stb::kids($rtd_k) { puts $rtd_f "K\t$rtd_n\t$rtd_c" }
  foreach rtd_s $::stb::sinks($rtd_k) { set rtd_a [stb::arr $rtd_s]; if {$rtd_a eq ""} { incr rtd_na; continue }
    set rtd_pp [get_pins -quiet $rtd_s]
    set rtd_e [get_property $rtd_pp [expr {[info exists ::stb::par($rtd_s)] && $::stb::par($rtd_s) ? "arrival_min_fall" : "arrival_min_rise"}]]
    if {$rtd_e eq "" || [string match *INF $rtd_e]} { set rtd_e $rtd_a } elseif {abs($rtd_e) < 1.0} { set rtd_e [expr {$rtd_e * 1e12}] }
    puts $rtd_f "S\t$rtd_n\t$rtd_s\t[format %.2f $rtd_a]\t[format %.2f $rtd_e]" }
  if {$rtd_n ne "PORT"} { set rtd_i [$rtd_blk findInst $rtd_n]; if {$rtd_i ne "NULL"} { lassign [$rtd_i getLocation] rtd_x rtd_y; puts $rtd_f "X\t$rtd_n\t$rtd_x\t$rtd_y" } }
}
close $rtd_f
# optional: full clock-expanded reports of named pin pairs (RTD_PAIRS = from1 to1 from2 to2 ..., odb-escaped names)
foreach {rtd_a rtd_b} [rtd_env RTD_PAIRS ""] { foreach rtd_m {max min} { puts "OT_RCK_PAIR $rtd_m $rtd_a -> $rtd_b"
  catch { report_checks -path_delay $rtd_m -from [get_pins $rtd_a] -to [get_pins $rtd_b] -format full_clock_expanded -digits 2 } } }
if {$rtd_ns > 0 && [file size [rtd_env RTD_OUT rck_tree.tsv]] == 0} { error "OT_RCK_TREE_DUMP: $rtd_ns sinks but nothing written" }
puts "OT_RCK_TREE_DUMP port $rtd_p nodes $rtd_nn sinks $rtd_ns no_arrival $rtd_na -> [rtd_env RTD_OUT rck_tree.tsv]"
