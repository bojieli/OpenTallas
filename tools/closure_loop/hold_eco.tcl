# CLOSURE-LOOP post-detailed-route FF hold ECO, ONE PASS (hold_eco.sh runs up to OT_PASSES of these, each followed by
# the sign-off corner_sta, and keeps the best result).  Adapted from the hub recipe
# physical/hbm_accel_die_views/common/post_route_hold_eco.tcl.
#
# Rev 2 (2026-10-07, systemic "ECO buffers destroy setup" class, 9 blocks):
#  * CONSTRAINTS = SIGN-OFF.  The session reads the corners' EFFECTIVE sign-off SDCs (hold_eco_corner.tcl: each built
#    in its own single-corner session exactly as corner_sta.py builds it, then write_sdc).  OT_SESSION=two: one
#    two-corner session on the SS/FF merge (hold_eco_sdc.py), used only when it reproduces sign-off (SS max and FF min
#    worst slack within 0.5 ps of the corner sessions).  Otherwise OT_SESSION=ff: an FF-only session on the FF file,
#    and setup is protected from the SS session's data (OT_SS_SLACK: SS setup slack per endpoint; OT_SS_CRIT: nets on
#    SS paths under the guard, dont_touch here).  Before rev 2 corner-conditional post-SDCs (vclk_corner_true.sdc)
#    were read once into a two-corner session: idxq_b1 saw SS vclk setup -414.69 where sign-off read +107.23, the
#    setup guard was void and 14,557 buffers took SS to -275.
#  * ENDPOINT FILTER (hold_eco_window.tcl): only endpoints with SS setup slack > deficit + OT_SETUP_FILTER (40) are
#    repaired; windows narrower than hm + accept_ss are reported INFEASIBLE (IO budget / RTL, never an ECO).
#  * HOLD TARGET 15 (OT_HOLD_MARGIN; was 22): the acceptance line, not 7 ps over it (hold_eco.sh re-passes residue).
#  * DELAY CELLS: HB1-4xp67 (ASAP7 hold buffers) are allowed for the repair (OT_HOLD_CELLS=1): one delay cell at the
#    capture pin replaces a chain of BUFx2 on the net.
#  * RESISTANCE-AWARE RE-ROUTE (OT_RES_AWARE=1), as the ORFS route's GRT: rev 1's plain re-route of all 47k nets put
#    ctrl_pc's worst SS path (k_rdy -> k_wdata[107]/D) on slower wires although no ECO cell sat on it: -77 ps
#    (data +97: _30517_ 44.5 -> 76.8 ps, place5356 58.5 -> 113.9 ps; clock +20).
#  * ITERATION: hold_eco.sh re-signs after each pass and runs a 2nd pass from the 1st pass's route.
# env: OT_DB, OT_SDC (effective / merged SDC), OT_SESSION (two|ff), OT_OUT, OT_MACROS, OT_HOLD_MARGIN (15),
#      OT_SETUP_MARGIN (40), OT_SETUP_FILTER (40), OT_ACCEPT_SS (15), OT_ACCEPT_FF (15), OT_HOLD_CELLS (1),
#      OT_RES_AWARE (1), OT_KEEP_CLOCK (0), OT_SS_SLACK, OT_SS_CRIT (ff session),
#      OT_SETUP_FIX (0; 1: a two-corner pass that starts under accept_ss + 10 first resizes setup -- segfaulted once in
#      repair_timing -setup on capt_x, so off by default), OT_GUIDES (1: keep the route's GRT guides, see below),
#      OT_WINDOW_ONLY (1: report the endpoint windows and stop), OT_THREADS (8), OT_MAX_BUF_PCT (30), OT_MINL/OT_MAXL (M2/M7), OT_MINCLKL (M4), OT_CL (helper dir)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
proc envd {n d} { expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d} }
set hm [envd OT_HOLD_MARGIN 21]; set sm [envd OT_SETUP_MARGIN 40]; set filt [envd OT_SETUP_FILTER 40]
set acc_ss [envd OT_ACCEPT_SS 15]; set acc_ff [envd OT_ACCEPT_FF 15]
set session [envd OT_SESSION two]
set_thread_count [envd OT_THREADS 8]
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach m [envd OT_MACROS ""] { read_lef $m/[file tail $m].lef }
set corners [expr {$session eq "two" ? {ss ff} : {ff}}]
define_corners {*}$corners
foreach c $corners {
  set C [string toupper $c]
  foreach l [list asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz \
               asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib \
               asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz] { read_liberty -corner $c $P/lib/NLDM/$l }
  foreach m [envd OT_MACROS ""] { read_liberty -corner $c $m/[file tail $m]_$c.lib }
}
read_db $::env(OT_DB)
read_sdc $::env(OT_SDC)
# no set_propagated_clock here: the effective SDC carries each clock's sign-off propagation state (write_sdc)
source $P/setRC.tcl
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
if {[envd OT_HOLD_CELLS 1]} { unset_dont_use [get_lib_cells */HB*xp67_ASAP7_75t_R] }
catch {remove_fillers}
source [envd OT_CL /cl]/hold_eco_window.tcl
proc rep {tag} {
  puts "OT_ECO $tag session $::session"
  report_worst_slack -max -digits 2
  report_worst_slack -min -digits 2
  catch {report_checks -path_delay min -scenes ff -format slack_only -digits 2}
  if {$::session eq "two"} { catch {report_checks -path_delay max -scenes ss -format slack_only -digits 2} }
}
proc ws {check scene} {
  # worst over every path group (find_timing_paths returns one path per group)
  set w 1e6
  foreach p [find_timing_paths -path_delay $check -scenes $scene -group_path_count 1] { set w [expr {min($w, [get_property $p slack])}] }
  return $w
}
set lo [envd OT_MINL M2]; set hi [envd OT_MAXL M7]
set_global_routing_layer_adjustment $lo-$hi 0.25
set_routing_layers -clock [envd OT_MINCLKL M4]-$hi
set_routing_layers -signal $lo-$hi
# RCX of the detailed route, annotated on every corner
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef $::env(OT_OUT)/pre_eco.spef
foreach c $corners { read_spef -corner $c $::env(OT_OUT)/pre_eco.spef }
rep pre
set ff0 [ws min ff]; set ss0 [expr {$session eq "two" ? [ws max ss] : "n/a"}]
puts "OT_ECO pre_ws ss $ss0 ff $ff0"
if {$session eq "two" && [envd OT_EXPECT_SS ""] ne ""} {
  # the two-corner session is exact only if its worst setup over BOTH corners is the SS sign-off and its worst hold over
  # both corners the FF sign-off (otherwise repair_timing also chases SS hold / guards FF setup)
  set amax [expr {[sta::worst_slack_cmd max] * 1e12}]; set amin [expr {[sta::worst_slack_cmd min] * 1e12}]
  if {abs($amax - $::env(OT_EXPECT_SS)) > 1.0 || abs($amin - $::env(OT_EXPECT_FF)) > 1.0} {
    puts [format "OT_ECO session_mismatch: two-corner worst setup %.2f / hold %.2f vs sign-off SS %s / FF %s -> FF-only session" \
      $amax $amin $::env(OT_EXPECT_SS) $::env(OT_EXPECT_FF)]
    exit
  }
}

# ---- setup protection data
if {$session eq "ff"} {
  # SS setup slack per endpoint (written by the SS corner session): the window filter reads it instead of slack_max
  set ::ot_ss_slack [dict create]
  if {[file exists [envd OT_SS_SLACK ""]]} {
    set f [open $::env(OT_SS_SLACK)]; while {[gets $f ln] >= 0} { if {[llength $ln] == 2} { dict set ::ot_ss_slack {*}$ln } }; close $f
  }
  set ncrit 0
  if {[file exists [envd OT_SS_CRIT ""]]} {
    set f [open $::env(OT_SS_CRIT)]
    while {[gets $f n] >= 0} { set nn [get_nets -quiet $n]; if {[llength $nn]} { set_dont_touch $nn; incr ncrit } }
    close $f
  }
  puts "OT_ECO ff session: [dict size $::ot_ss_slack] SS endpoint slacks, $ncrit SS-critical nets dont_touch"
}

# ---- optional setup recovery first (a pass that starts under the acceptance line + 10)
set n0 [llength [get_cells *]]
if {$session eq "two" && [envd OT_SETUP_FIX 0] && $ss0 < $acc_ss + 10} {
  puts "OT_ECO setup_fix: SS $ss0 < [expr {$acc_ss + 10}]: resize / swap only"
  catch {repair_timing -setup -setup_margin [expr {$acc_ss + 10}] -skip_buffering -skip_gate_cloning -verbose} err
}

# ---- endpoint filter: repair only endpoints whose setup can absorb the deficit + filt
# window: endpoints under the repair target (post-route goal + allowance, from hold_eco.sh)
set win [ot_window $hm $filt $acc_ss pre]
if {[envd OT_WINDOW_ONLY 0]} { puts "OT_ECO window_only"; exit }
set nx 0
foreach k {tight infeasible} { foreach ep [dict get $win $k] { set_false_path -hold -to $ep; incr nx } }
puts "OT_ECO filter: [llength [dict get $win fixable]] endpoints repaired, $nx excluded (tight/infeasible stay as they are)"

# ---- snapshot, repair, legalise
set block [ord::get_db_block]
# GUIDE-PRESERVING re-route (OT_GUIDES=1, default): the routed db still holds the route's GRT guides (grt::have_routes).
# Incremental GRT around the repair re-guides only the nets the ECO touches; every wire is then stripped and DRT routes
# from scratch on the ORIGINAL guides for all untouched nets.  Measured on ctrl_pc 3f0455126 with NO ECO cell at all:
# strip + fresh GRT + DRT alone took SS +70.18 -> +5.98 and FF -4.20 -> -2.06, i.e. the whole "ECO kills setup" loss
# was the fresh global route, not the hold buffers.  (Keeping untouched WIRES instead fails in DRT: 1,300-2,800
# 'pin not visited' + checkConnectivity on untouched nets; keeping clock wires fails checkConnectivity.)
set guides [expr {[envd OT_GUIDES 1] && [grt::have_routes]}]
puts "OT_ECO route guides from the db: $guides"
if {$guides} { global_route -start_incremental }
set snap [dict create]
foreach i [$block getInsts] { dict set snap [$i getName] [list {*}[$i getLocation] [$i getOrient] [[$i getMaster] getName]] }
if {[llength [dict get $win fixable]]} {
  if {[catch {repair_timing -hold -hold_margin $hm -setup_margin $sm -max_buffer_percent [envd OT_MAX_BUF_PCT 30] -verbose} err]} {
    error "OT_ECO repair_timing failed: $err"
  }
}
puts "OT_ECO cells_added [expr {[llength [get_cells *]] - $n0}]"
detailed_placement
check_placement -verbose

# ---- re-route: every signal wire stripped and re-routed (OT_KEEP_CLOCK=1 keeps the clock's detailed wires).
# A partial re-route (wires of untouched nets kept) does not work with this DRT: kept wires + fresh or incremental GRT
# guides gave 1,300-2,800 'pin not visited' and checkConnectivity breaks on UNTOUCHED nets (ctrl_pc, 2026-10-07).
# The re-route is RESISTANCE-AWARE like the ORFS route's GRT (global_route -resistance_aware): rev 1 re-routed without
# it, and ctrl_pc's worst SS path (k_rdy -> k_wdata[107]/D, no ECO cell on it) lost 77 ps on new, slower wires.
set ninst 0
foreach i [$block getInsts] {
  set n [$i getName]
  if {![dict exists $snap $n] || [dict get $snap $n] ne [list {*}[$i getLocation] [$i getOrient] [[$i getMaster] getName]]} { incr ninst }
}
set nstrip 0
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} continue
  if {[envd OT_KEEP_CLOCK 0] && [$net getSigType] eq "CLOCK"} continue
  set w [$net getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nstrip }
}
puts "OT_ECO reroute: $ninst new/moved/resized instances, $nstrip wires stripped"
set ra [expr {[envd OT_RES_AWARE 1] ? "-resistance_aware" : ""}]
if {$guides} { global_route -end_incremental -allow_congestion {*}$ra } else { global_route -allow_congestion -congestion_iterations 30 {*}$ra }
if {[catch {detailed_route -output_drc $::env(OT_OUT)/eco_drc.rpt -verbose 1} err]} {
  # a db whose guides came from an earlier ECO pass can carry a guide DRT rejects (capt_x pass 2: DRT-0218 'Guide is
  # not connected to design'): fall back to a fresh resistance-aware global route for this pass
  if {!$guides} { error "OT_ECO detailed_route failed: $err" }
  puts "OT_ECO guide re-route failed ($err): fresh global route"
  foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} continue
    set w [$net getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w }
  }
  global_route -allow_congestion -congestion_iterations 30 {*}$ra
  detailed_route -output_drc $::env(OT_OUT)/eco_drc.rpt -verbose 1
}
filler_placement {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R}
check_placement -verbose
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef $::env(OT_OUT)/6_final.spef
foreach c $corners { read_spef -corner $c $::env(OT_OUT)/6_final.spef }
rep post
puts "OT_ECO post_ws ss [expr {$session eq "two" ? [ws max ss] : "n/a"}] ff [ws min ff]"
write_db $::env(OT_OUT)/6_final.odb
write_verilog $::env(OT_OUT)/6_final.v
puts "OT_ECO done"
