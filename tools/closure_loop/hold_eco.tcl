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
#  * ENDPOINT FILTER (hold_eco_window.tcl): only endpoints with SS setup slack > r x deficit + OT_SETUP_FILTER (40) are
#    repaired, r = OT_SS_FF_RATIO (2.4: a ps of FF hold delay costs ~2.4 ps at SS; with r = 1 the FF-only session on
#    idxq_b1 took SS +107 -> -142).  Endpoints that cannot reach accept_ff with SS >= accept_ss are INFEASIBLE.
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
set corners [expr {$session in {two mm} ? {ss ff} : {ff}}]
if {$session eq "mm"} {
  # REV 3 MULTI-MODE session (default): scene ss = mode ss (the SS effective sign-off SDC, hold false-pathed) on SS libs,
  # scene ff = mode ff (the FF effective SDC, setup false-pathed) on FF libs.  Every check is timed exactly as sign-off
  # times it, so repair_timing's own -setup_margin guard sees real SS setup when it places each hold cell.  (FF-only
  # session: dshead-ctl-r6 gained 27 ps FF hold on commit_warm with 6 HB4 cells and lost 423 ps SS setup, +87.9 ->
  # -335.7; the same repair in this session ends SS +41.9 / FF +21.0.)
  foreach c $corners {
    set C [string toupper $c]; set L($c) {}
    foreach l [list asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz \
                 asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib \
                 asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz] { read_liberty $P/lib/NLDM/$l; lappend L($c) $P/lib/NLDM/$l }
    foreach m [envd OT_MACROS ""] { read_liberty $m/[file tail $m]_$c.lib; lappend L($c) $m/[file tail $m]_$c.lib }
  }
  read_db $::env(OT_DB)
  read_sdc -mode ss $::env(OT_SDC_SS)
  read_sdc -mode ff $::env(OT_SDC_FF)
  define_scene ss -mode ss -liberty $L(ss)
  define_scene ff -mode ff -liberty $L(ff)
  # port loads / drivers / input slews read before the scenes exist do not reach them (ctl r6 o_we[3]: output buffer
  # 13.4 ps unloaded vs 18.4 ps at sign-off, FF hold -65.95 vs -60.14): re-apply them per mode after define_scene
  foreach m {ss ff} f [list $::env(OT_SDC_SS) $::env(OT_SDC_FF)] {
    set envf $::env(OT_OUT)/env_$m.sdc
    set fi [open $f]; set fo [open $envf w]
    foreach l [split [read $fi] "\n"] { if {[regexp {^(set_load|set_driving_cell|set_input_transition)\M} $l]} { puts $fo $l } }
    close $fi; close $fo
    set_mode $m
    source $envf
  }
} else {
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
}
# no set_propagated_clock here: the effective SDC carries each clock's sign-off propagation state (write_sdc)
source $P/setRC.tcl
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
# rev 3: only the SMALL hold cells HB1/HB2 (HB3/HB4 add ~70-110 ps at SS each; ctl r6 stacked six HB4 for 27 ps of FF)
if {[envd OT_HOLD_CELLS 1]} { unset_dont_use [get_lib_cells {*/HB1xp67_ASAP7_75t_R */HB2xp67_ASAP7_75t_R}] }
catch {remove_fillers}
source [envd OT_CL /cl]/hold_eco_window.tcl
proc rep {tag} {
  puts "OT_ECO $tag session $::session"
  report_worst_slack -max -digits 2
  report_worst_slack -min -digits 2
  catch {report_checks -path_delay min -scenes ff -format slack_only -digits 2}
  if {$::session in {two mm}} { catch {report_checks -path_delay max -scenes ss -format slack_only -digits 2} }
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
# parasitics of the route: the SAME SPEF the sign-off / corner sessions read (OT_PRE_SPEF, rev 3), so the session's
# worst slacks reproduce sign-off exactly (a fresh RCX of 5_2_route.odb read FF -65.95 against sign-off -60.14 on
# dshead-ctl-r6); fresh RCX only when no SPEF is given
if {[file exists [envd OT_PRE_SPEF ""]]} {
  foreach c $corners { read_spef -corner $c $::env(OT_PRE_SPEF) }
} else {
  extract_parasitics -ext_model_file $P/rcx_patterns.rules
  write_spef $::env(OT_OUT)/pre_eco.spef
  foreach c $corners { read_spef -corner $c $::env(OT_OUT)/pre_eco.spef }
}
rep pre
set ff0 [ws min ff]; set ss0 [expr {$session in {two mm} ? [ws max ss] : "n/a"}]
puts "OT_ECO pre_ws ss $ss0 ff $ff0"
if {$session in {two mm} && [envd OT_EXPECT_SS ""] ne ""} {
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
set ::ot_ss_ff_ratio [envd OT_SS_FF_RATIO 2.4]
set win [ot_window $hm $filt $acc_ss pre $acc_ff]
if {[envd OT_WINDOW_ONLY 0]} { puts "OT_ECO window_only"; exit }
set nx 0
foreach k {tight infeasible nodata} { foreach ep [dict get $win $k] { set_false_path -hold -to $ep; incr nx } }
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
set allow_fresh [envd OT_ALLOW_FRESH_GRT 0]
puts "OT_ECO route guides from the db: $guides"
if {$guides} {
  puts "OT_ECO route_strategy incremental_original_guides"
  global_route -start_incremental
} elseif {$allow_fresh} {
  puts "OT_ECO route_strategy fresh_global reason missing_original_guides explicit_opt_in 1"
} else {
  error "OT_ECO original guides unavailable; fresh GRT requires OT_ALLOW_FRESH_GRT=1"
}
set snap [dict create]
foreach i [$block getInsts] { dict set snap [$i getName] [list {*}[$i getLocation] [$i getOrient] [[$i getMaster] getName]] }
if {[llength [dict get $win fixable]]} {
  if {[catch {repair_timing -hold -hold_margin $hm -setup_margin $sm -max_buffer_percent [envd OT_MAX_BUF_PCT 30] -verbose} err]} {
    error "OT_ECO repair_timing failed: $err"
  }
}
# rev 3 SETUP GUARD (a): every SS path that now sits under the setup margin loses the ECO cells on it (they are removed
# with remove_buffers); its hold endpoint stays as it was and the verdict reports it.  Needs SS timing: mm/two only.
if {$session in {two mm} && [envd OT_SETUP_GUARD 1]} {
  set newc [dict create]
  foreach i [$block getInsts] { if {![dict exists $snap [$i getName]]} { dict set newc [$i getName] 1 } }
  set undo [dict create]
  set guard_paths [find_timing_paths -path_delay max -scenes ss -slack_max $sm -group_path_count 100000 -endpoint_path_count 1]
  set rows {}
  foreach pe $guard_paths { if {![catch {set pts [get_property $pe points]}]} { lappend rows $pts } }
  foreach pts $rows {
    foreach pt $pts {
      if {[catch {set pin [get_property $pt pin]}] || $pin eq "NULL"} continue
      if {[catch {set inst [get_full_name [get_cells -of_objects $pin]]}]} continue
      if {[dict exists $newc $inst]} { dict set undo $inst 1 }
    }
  }
  if {[dict size $undo]} {
    remove_buffers [get_cells [dict keys $undo]]
    puts "OT_ECO setup_guard removed [dict size $undo] ECO cells on [llength $rows] SS paths under $sm ps"
  } else { puts "OT_ECO setup_guard: no ECO cell on an SS path under $sm ps" }
  puts "OT_ECO after_guard ss [ws max ss] ff [ws min ff]"
}
puts "OT_ECO cells_added [expr {[llength [get_cells *]] - $n0}]"
detailed_placement
check_placement -verbose

# ---- re-route: every signal wire stripped and re-routed (OT_KEEP_CLOCK=1 keeps the clock's detailed wires).
# A partial re-route (wires of untouched nets kept) does not work with this DRT: kept wires + fresh or incremental GRT
# guides gave 1,300-2,800 'pin not visited' and checkConnectivity breaks on UNTOUCHED nets (ctrl_pc, 2026-10-07).
# The re-route is RESISTANCE-AWARE like the ORFS route's GRT (global_route -resistance_aware): rev 1 re-routed without
# it, and ctrl_pc's worst SS path (k_rdy -> k_wdata[107]/D, no ECO cell on it) lost 77 ps on new, slower wires.
set ninst 0; set dirty [dict create]
foreach i [$block getInsts] {
  set n [$i getName]
  if {![dict exists $snap $n] || [dict get $snap $n] ne [list {*}[$i getLocation] [$i getOrient] [[$i getMaster] getName]]} {
    incr ninst
    foreach it [$i getITerms] { set nt [$it getNet]; if {$nt ne "NULL"} { dict set dirty [$nt getName] 1 } }
  }
}
# rev 3 MACRO-NET FREEZE (OT_FREEZE_MACRO_NETS=1, OFF by default: on hbm_cmdproc_n with 64 frozen nets DRT finished but
# the session then failed with a corrupted Tcl command name ('filler_plf') -- not safe to enable yet): nets driven by a macro output keep their detailed wires unless the ECO
# touched them (a new / moved / resized cell on the net).  Qwen slab s14 (guide-preserving ECO): the re-route
# re-detoured ROM -> capture-register nets, worst register-D setup +44.55 -> +4.66 while reg2reg stayed +122.  If DRT
# rejects the kept wires, they are stripped and DRT runs again (logged).
set frozen {}
if {[envd OT_FREEZE_MACRO_NETS 0]} {
  foreach i [$block getInsts] {
    if {![[$i getMaster] isBlock]} continue
    foreach it [$i getITerms] {
      if {![$it isOutputSignal]} continue
      set nt [$it getNet]
      if {$nt eq "NULL" || [dict exists $dirty [$nt getName]] || [$nt getSigType] in {POWER GROUND CLOCK}} continue
      lappend frozen $nt
    }
  }
}
set fz [dict create]; foreach nt $frozen { dict set fz [$nt getName] 1 }
set nstrip 0
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} continue
  if {[envd OT_KEEP_CLOCK 0] && [$net getSigType] eq "CLOCK"} continue
  if {[dict exists $fz [$net getName]]} continue
  set w [$net getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nstrip }
}
puts "OT_ECO reroute: $ninst new/moved/resized instances, $nstrip wires stripped, [dict size $fz] macro-output nets frozen"
set ra [expr {[envd OT_RES_AWARE 1] ? "-resistance_aware" : ""}]
if {$guides} { global_route -end_incremental -allow_congestion {*}$ra } else { global_route -allow_congestion -congestion_iterations 30 {*}$ra }
# Preserve guides by default because fresh GRT has measured setup-regression
# risk. An explicitly requested fallback is valid if the unchanged final
# timing, DRC, IO and context checks pass; route strategy is not acceptance.
set drt_err [catch {detailed_route -output_drc $::env(OT_OUT)/eco_drc.rpt -verbose 1} err]
if {$drt_err && [info exists fz] && [dict size $fz]} {
  puts "OT_ECO macro-net freeze rejected by DRT ($err): frozen wires stripped, DRT again"
  foreach nt $frozen { set w [$nt getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w } }
  set drt_err [catch {detailed_route -output_drc $::env(OT_OUT)/eco_drc.rpt -verbose 1} err]
}
if {$drt_err} {
  if {!$guides || !$allow_fresh} { error "OT_ECO detailed_route failed: $err" }
  puts "OT_ECO guide re-route failed ($err): explicitly requested fresh global route"
  puts "OT_ECO route_strategy fresh_global reason rejected_guides explicit_opt_in 1"
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
puts "OT_ECO post_ws ss [expr {$session in {two mm} ? [ws max ss] : "n/a"}] ff [ws min ff]"
write_db $::env(OT_OUT)/6_final.odb
write_verilog $::env(OT_OUT)/6_final.v
puts "OT_ECO done"
