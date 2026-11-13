# FLOW-CLOCK-R7 2026-10-29: shared post-route drive (DRV) repair on the core's ROUTED RCX parasitics, one pass
# (ORFS POST_GLOBAL_ROUTE_TCL hook staged by tools/die_plan/post_route_drv/prd_mk.sh; die-agnostic, opt-in).
# Recipe = KV eco_route.tcl m-order (DRV first on the routed SPEF, setup, hold: the e1/e5/e7 signed-off order) started
# from the kit's PRE-DRT 5_1_grt.odb (FLOW-SHARED-10 grt form, ONE detailed route afterwards), with the three fixes the
# R6 HBM bdring canary measured (lanes/COORD-REVIEW-QUEUE.md 10-29 16:31):
#   (1) the two-mode hold session: the runner patches orfs_hold_mm.py into the container (kit_modes_eco.tcl checks it);
#   (2) clock-freeze cells keep their masters: clk_freeze LOCKs every instance on a clock net, but sink flops are not
#       dont_touch (hold buffers must reach their D pins, RSZ-3006), so the R6 setup repair upsized 33 LOCKED
#       DFFHQNx1 -> x2 in place = 16 overlaps at fill (DPL-0033).  Here every master family used by a clock-net sink is
#       set_dont_use for the ECO session (no sink can be resized; buffering at its pins is unchanged), and a fail-safe
#       guard reverts + reports any frozen instance whose master still changed before legalization;
#   (3) the <= 2-pass loop is in prd_run.sh (re-extract RCX after DRT, repeat only while slew/cap violations remain).
# Limits are the existing sign-off ones (liberty max_transition / max_capacitance; no fanout limit unless
# OT_PRD_MAX_FANOUT opts in (R8), repair margins 20 %); no corner, margin or check kind changes.
#   OT_MAX_FANOUT OT_SLEW_MARGIN OT_SETUP_MARGIN OT_HOLD_MARGIN OT_HOLD_ALLOW_SETUP OT_HOLD_MAXBUF  (as eco_route.tcl)
#   OT_PRD_PASS (1|2, log only)
set _here [file dirname [info script]]
# FLOW-11 10-30 (DIE-QC-50 BTAB, CHECKED there): the ECO session read the routed SPEF once, but every later
# estimate_parasitics (two-mode ot_mm_sync before each repair, ot_rc_cal_hold, the measured-FF IO frame of
# vclk_measured_hold.tcl, the kit's post-GRT hook) overwrote it with the global-route estimate, so hold repair and the
# IO virtual-clock frame were timed on estimates, not on the routed DB (BTAB wd_in[227]: session 22.82 vs sign-off
# -4.29; -4.29 once the routed SPEF is re-read).  ot_prd_spef_arm reads the routed SPEF into every scene of the session
# (two-mode: the setup scene and BC; else the one corner) and re-reads it after each native estimate_parasitics:
# every existing net keeps its routed RCX parasitics, nets the ECO creates keep the estimate.  No check or margin
# changes.  OT_PRD_ROUTED_SPEF=0 = the old single read (A/B only).
proc ot_prd_spef_read {why} {
  set f $::ot_prd_spef
  set rf $f
  set note ""
  if {[info exists ::ot_prd_conn_ref]} {
    set ch [ot_prd_conn_changed]
    if {[dict size $ch]} {
      lassign [ot_prd_spef_without $f $ch] rf nskip
      set note ", [dict size $ch] ECO-changed nets keep the estimate ($nskip routed SPEF nets skipped)"
    }
  }
  set scs {}
  try {
    if {[info exists ::ot_mm_active] && $::ot_mm_active && [llength [info commands ot_mm_sc]]} {
      set scs [list [ot_mm_sc] BC]
      foreach sc $scs { read_spef -corner $sc $rf }
    } else {
      read_spef $rf
    }
  } finally {
    if {$rf ne $f} { file delete $rf }
  }
  incr ::ot_prd_spef_reads
  puts "OT_PRD_SPEF $why: read_spef [expr {[llength $scs] ? "-corner {$scs} " : ""}][file tail $f] (read $::ot_prd_spef_reads$note)"
}
# FLOW-CLASS-25 11-06 (COORD 18:0x (3a), DIE-HBM-82-Q3EL 15:46): the re-read put the routed SPEF back onto nets whose
# connectivity the ECO had changed.  q3_edge_link eco4: repair_design split 55 nets with 38 buffers, the next re-read gave
# 1001 STA-1651 "not connected" on 35 of them, the split nets lost their routed wire delay in the session (D-side wire of
# bank dq[*] -> SRAM wd_in), the session showed a false FF hold -33.19 (sign-off on the same DB: about 0), and the guarded
# hold repair put 1900 buffers on 1899 near-zero endpoints.  Now the connectivity of every signal net is recorded when the
# SPEF is armed (instance terminals + ports, as prd_route_keep.tcl judges it), and each later re-read skips the SPEF
# section of every net whose connectivity changed since: such a net keeps the estimate the native estimate_parasitics
# just gave it, like the nets the ECO created.  Unchanged nets get the routed SPEF exactly as before.  Sign-off
# re-extracts the routed result, so no check, margin or corner changes.  OT_PRD_SPEF_CHANGED=reread = the old re-read.
proc ot_prd_conn_sig {n} {
  set l {}
  foreach t [$n getITerms] { lappend l [$t getId] }
  foreach t [$n getBTerms] { lappend l b[$t getId] }
  return [lsort $l]
}
proc ot_prd_conn_snapshot {} {
  set d [dict create]
  foreach n [[ord::get_db_block] getNets] {
    if {[$n getSigType] in {POWER GROUND}} continue
    dict set d [$n getName] [ot_prd_conn_sig $n]
  }
  return $d
}
# -> dict {name -> 1} of the armed nets that are gone or whose connectivity changed; names without escapes (SPEF and
# OpenDB escape differently, see ot_prd_stage_check)
proc ot_prd_conn_changed {} {
  set block [ord::get_db_block]
  set ch [dict create]
  dict for {k sig} $::ot_prd_conn_ref {
    set n [$block findNet $k]
    if {$n eq "NULL" || $n eq "" || [ot_prd_conn_sig $n] ne $sig} { dict set ch [string map {\\ {}} $k] 1 }
  }
  return $ch
}
# copy of SPEF f without the *D_NET sections of the nets in changed (name map resolved) -> {file skipped}
proc ot_prd_spef_without {f changed} {
  set out [file join [file dirname $f] ot_prd_eco_[pid]_[clock clicks].spef]
  set in [open $f r]; set fo [open $out w]
  fconfigure $in -buffersize 1048576; fconfigure $fo -buffersize 1048576
  set map [dict create]; set inmap 0; set skip 0; set nskip 0
  while {[gets $in ln] >= 0} {
    if {$skip} {
      if {[string trim $ln] eq "*END"} { set skip 0 }
      continue
    }
    if {[string index $ln 0] eq "*"} {
      if {[string match {\*D_NET*} $ln]} {
        set inmap 0
        if {[regexp {^\*D_NET\s+(\S+)} $ln -> nm]} {
          if {[dict exists $map $nm]} { set nm [dict get $map $nm] }
          if {[dict exists $changed [string map {\\ {}} $nm]]} { set skip 1; incr nskip; continue }
        }
      } elseif {[string match {\*NAME_MAP*} $ln]} {
        set inmap 1
      } elseif {$inmap} {
        if {[regexp {^(\*[0-9]+)\s+(\S+)} $ln -> idx nm]} { dict set map $idx $nm } else { set inmap 0 }
      }
    }
    puts $fo $ln
  }
  close $in; close $fo
  return [list $out $nskip]
}
proc ot_prd_spef_arm {f} {
  if {[info exists ::env(OT_PRD_ROUTED_SPEF)] && $::env(OT_PRD_ROUTED_SPEF) eq "0"} {
    puts "OT_PRD_SPEF off (OT_PRD_ROUTED_SPEF=0): one read, later estimates overwrite it"
    read_spef $f
    return
  }
  set ::ot_prd_spef $f
  set ::ot_prd_spef_reads 0
  unset -nocomplain ::ot_prd_conn_ref
  ot_prd_spef_read entry
  if {[info exists ::env(OT_PRD_SPEF_CHANGED)] && $::env(OT_PRD_SPEF_CHANGED) eq "reread"} {
    puts "OT_PRD_SPEF changed nets: re-read like every other net (OT_PRD_SPEF_CHANGED=reread)"
  } elseif {[llength [info commands ::ord::get_db_block]]} {
    set ::ot_prd_conn_ref [ot_prd_conn_snapshot]
    puts "OT_PRD_SPEF connectivity of [dict size $::ot_prd_conn_ref] signal nets recorded: a net the ECO changes keeps its estimate"
  }
  if {[llength [info commands ::ot_prd_native_estimate]]} { return }
  # no native estimator in this interpreter (tclsh harnesses, sessions without RSZ): nothing to re-read after
  if {![llength [info commands ::estimate_parasitics]]} { return }
  rename ::estimate_parasitics ::ot_prd_native_estimate
  proc ::estimate_parasitics {args} {
    # OT_PRD_REPAIR_RC=placement (DIE-S81-48 11-02): during the repair calls every global-routing estimate is a
    # placement estimate (see below); existing nets still get the routed SPEF re-read right after
    if {[info exists ::ot_prd_rc_place] && $::ot_prd_rc_place} {
      set args [lmap a $args {expr {$a eq "-global_routing" ? "-placement" : $a}}]
    }
    set r [uplevel 1 [list ::ot_prd_native_estimate {*}$args]]
    ot_prd_spef_read "after estimate_parasitics $args"
    return $r
  }
}
# DIE-S81-50 11-03 (class fix, stale-staging class): the SPEF must belong to the seed DB.  S81 l4: kit 6_final.{odb,
# spef} = a post-route hold ECO (1,305 hxeco_* buffers) the seed 5_2_route.odb predates -> 1,000+ STA-1648 "instance
# not found" on read_spef, then RSZ-0074 "found route to 23 pins, expected 24" in repair_design 30 min later.  Every
# logic instance the SPEF connects (prd_spef_insts.py list, staged by prd_mk.sh; antenna/filler/tap/decap skipped)
# must exist in the seed, else OT_PRD STAGE_MISMATCH at once (prd_mk.sh OT_PRD_FROM=final seeds such a kit with its
# own 6_final.odb).  No list (older pass dir) = no check; OT_PRD_STAGE_CHECK=0 = off.  No timing check changes.
proc ot_prd_stage_check {list} {
  if {[info exists ::env(OT_PRD_STAGE_CHECK)] && $::env(OT_PRD_STAGE_CHECK) eq "0"} { puts "OT_PRD stage check off"; return }
  if {![file exists $list]} { puts "OT_PRD stage check: no [file tail $list] (pass dir predates the check)"; return }
  set block [ord::get_db_block]
  set n 0; set miss {}
  set fh [open $list r]
  while {[gets $fh ln] >= 0} {
    set name [lindex [split $ln " "] 0]
    if {$name eq ""} continue
    incr n
    set found 0
    # HBM-FORM-SPLIT-12 11-06: yosys merged-register names hold a literal backslash (u_x._1_[0]$\u_x._1_[1]$dff[0]).
    # SPEF writes u_x\._1_\[0\]\$\\u_x..., OpenDB keeps u_x._1_\[0\]$\\u_x... (brackets and the backslash stay escaped,
    # . and $ do not), so the third candidate unescapes \X but keeps a \\ pair (Q2NF: 2322 of 12396 false misses -> 0)
    # DIE-S81-82 11-08: hierarchical names keep the \/ divider in OpenDB too: SPEF u_bound\.u_x\/_4_, OpenDB
    # u_bound.u_x\/_4_, so the last candidate unescapes \X but keeps \/ and brackets (t51 vD: 58218 of 116412 false misses -> 0)
    foreach cand [list $name [regsub -all {\\([^\[\]])} $name {\1}] [regsub -all {\\([^\[\]\\])|(\\\\)} $name {\1\2}] \
        [string map {\\ {}} $name] [regsub -all {\\([^\[\]/])} $name {\1}]] {
      set i [$block findInst $cand]
      if {$i ne "NULL" && $i ne ""} { set found 1; break }
    }
    if {!$found} { lappend miss $ln }
  }
  close $fh
  if {[llength $miss]} {
    error "OT_PRD STAGE_MISMATCH: [llength $miss] of $n SPEF logic instances are not in the seed DB (SPEF from another\
      netlist, e.g. a post-route ECO'd 6_final; use OT_PRD_FROM=final): [lrange $miss 0 9]"
  }
  puts "OT_PRD stage check: all $n SPEF logic instances in the seed DB"
}
# OT_PRD_FROM=final (prd_mk.sh): the seed is the kit's signed 6_final.odb; its filler cells go before any repair (the
# ECO legalizes new cells; ORFS fill runs again after the ECO route).  Fillers carry no signal net.
if {[info exists ::env(OT_PRD_FROM)] && $::env(OT_PRD_FROM) eq "final"} {
  remove_fillers
  puts "OT_PRD seed final: 6_final.odb, fillers removed"
}
if {[info exists ::env(OT_MM_FROZEN_CLOCK_SPEFS)] && $::env(OT_MM_FROZEN_CLOCK_SPEFS) ne ""} {
  # The native estimator already supplied DATA RC and the early MM callback
  # restored only the immutable frozen clock. Never replay an old full SPEF or
  # reset the original freeze baseline here.
  if {![llength [info commands ::ot_mm_frozen_clock_rc_restore]]} {
    error "OT_MM_FROZEN_CLOCK_RC: early lifecycle helper missing before PRD"
  }
  ::ot_mm_frozen_clock_rc_restore prd_entry
} else {
  ot_prd_stage_check /work/prd_spef_insts.tsv
  if {[info exists ::env(OT_PRD_TARGETED)] && $::env(OT_PRD_TARGETED) eq "1"} { source [file join $_here prd_tiesplit.tcl] }
  ot_prd_spef_arm $::env(RESULTS_DIR)/6_final.spef
  set _ckf [file join $_here clk_freeze.tcl]
  if {![file exists $_ckf]} { error "OT_CLK_FREEZE FAIL: $_ckf not staged (ECO refuses to run without the clock lock)" }
  source $_ckf
  ot_clk_freeze
}
# A measured OpenROAD route-tree defect may require preserving a specific data
# net during ECO (e.g. three tiny QUERY terminals coalesced into one GCell).
# This changes repair eligibility only; normal STA/DRV and frozen-clock checks
# still decide the result. Exact names only, and never a clock or supply net.
# DIE-HEAD-59 11-03 (opt-in, DRC class Rect Only on a wide landing pin): landing_contract.io_tcl draws scalar landing
# pins 0.080 wide on M7; a 0.032 DRT stub entering such a pin from outside makes a non-rectangular shape, RECTONLY M7
# (hd_st_n3_turn rst_start_raw_2 + hd_host_n rst_start_raw_0: same 3 markers through a full re-route).
# OT_PRD_NARROW_PINS = exact port names: same centre, same length, layer default width; the net is re-routed.
set ::ot_prd_force_rip {}
if {[info exists ::env(OT_PRD_NARROW_PINS)] && $::env(OT_PRD_NARROW_PINS) ne ""} {
  foreach _pn $::env(OT_PRD_NARROW_PINS) {
    set _bt [[ord::get_db_block] findBTerm $_pn]
    if {$_bt eq "NULL" || $_bt eq ""} { error "OT_PRD_NARROW_PINS requires an exact existing port: $_pn" }
    foreach _bp [$_bt getBPins] {
      foreach _bx [$_bp getBoxes] {
        set _ly [$_bx getTechLayer]; set _w [$_ly getWidth]
        set _x0 [$_bx xMin]; set _x1 [$_bx xMax]; set _y0 [$_bx yMin]; set _y1 [$_bx yMax]
        if {[$_ly getDirection] eq "VERTICAL"} {
          if {$_x1 - $_x0 <= $_w} continue
          set _c [expr {($_x0 + $_x1) / 2}]; set _x0 [expr {$_c - $_w / 2}]; set _x1 [expr {$_x0 + $_w}]
        } else {
          if {$_y1 - $_y0 <= $_w} continue
          set _c [expr {($_y0 + $_y1) / 2}]; set _y0 [expr {$_c - $_w / 2}]; set _y1 [expr {$_y0 + $_w}]
        }
        odb::dbBox_destroy $_bx
        odb::dbBox_create $_bp $_ly $_x0 $_y0 $_x1 $_y1
        puts "OT_PRD_NARROW_PINS $_pn [$_ly getName] -> $_x0 $_y0 $_x1 $_y1 (dbu)"
      }
    }
    lappend ::ot_prd_force_rip [[$_bt getNet] getName]
  }
}
if {[info exists ::env(OT_PRD_PROTECT_NETS)] && $::env(OT_PRD_PROTECT_NETS) ne ""} {
  foreach name $::env(OT_PRD_PROTECT_NETS) {
    set dbnet [[ord::get_db_block] findNet $name]
    set nets [get_nets -quiet $name]
    if {$dbnet eq "NULL" || $dbnet eq "" || [llength $nets] != 1
        || [get_full_name [lindex $nets 0]] ne $name} {
      error "OT_PRD_PROTECT_NETS requires an exact existing net: $name"
    }
    if {[$dbnet getSigType] in {CLOCK POWER GROUND} || $dbnet in [ot_clk_dbnets]} {
      error "OT_PRD_PROTECT_NETS requires a data net: $name"
    }
    set_dont_touch $nets
    puts "OT_PRD_PROTECT_NETS preserved data net $name (all signoff checks retained)"
  }
}
# DIE-S81-50 11-03 (class fix, gated-clock-cell data-pin class): ot_clk_freeze dont_touches every clock-tree cell,
# including ICGs, whose ENA (and SE) pins are DATA loads.  repair_design / hold repair buffering such a net then dies:
# ODB-1211 "InsertBufferBeforeLoads: Load pin 'ot_rtg_icg0_2/ENA' is dont_touch" -> RSZ-3006 fatal (S81 rom, rom_t:
# net10319 is a slew/cap-violating ENA net, so dont_touching the net would leave the DRV).  For the repair calls only,
# a clock-tree cell with a non-clock input on a data net drops dont_touch; it stays LOCKED (no move), its master family
# goes into the session's set_dont_use with the sinks' (no resize), the master revert guard covers it, and dont_touch is
# put back before legalization; the clock nets stay dont_touch (no buffering of its output) and clk_freeze_check.sh
# stays blocking.  OT_PRD_CLKCELL_DATA_PINS=0 restores the old freeze.
set ::ot_prd_dtoff {}
if {![info exists ::env(OT_PRD_CLKCELL_DATA_PINS)] || $::env(OT_PRD_CLKCELL_DATA_PINS) ne "0"} {
  set _cknets [dict create]; set _ckdrv [dict create]
  foreach n [ot_clk_dbnets] {
    dict set _cknets [$n getName] 1
    foreach it [$n getITerms] { if {[$it isOutputSignal]} { dict set _ckdrv [[$it getInst] getName] [$it getInst] } }
  }
  dict for {i inst} $_ckdrv {
    if {![$inst isDoNotTouch]} continue
    foreach it [$inst getITerms] {
      if {![$it isInputSignal]} continue
      set net [$it getNet]
      if {$net eq "NULL" || $net eq ""} continue
      if {[dict exists $_cknets [$net getName]] || [$net getSigType] in {CLOCK POWER GROUND}} continue
      $inst setDoNotTouch 0
      lappend ::ot_prd_dtoff $i
      break
    }
  }
  puts "OT_PRD clock-tree cells with data input pins: dont_touch off for the repair (LOCKED, family dont_use, revert guard) [llength $::ot_prd_dtoff] [lrange $::ot_prd_dtoff 0 9]"
}
proc ot_prd_dtoff_restore {} {
  foreach i $::ot_prd_dtoff { [[ord::get_db_block] findInst $i] setDoNotTouch 1 }
  puts "OT_PRD clock-tree cells dont_touch restored [llength $::ot_prd_dtoff]"
}
# OT_PRD_REPAIR_RC=placement (DIE-S81-48 11-02, class fix): with the GRT parasitics source every resizer move calls
# GlobalRouter::updateDirtyRoutes -> TritonRoute::updateDirtyPAData, and FlexPA crashes (SIGSEGV in getEdgeCost /
# FlexGCWorker::initPA0) on the not-yet-legalized ECO cells: S81 l1c A/B and l4 die at the first
# setup-repair move (run_prd.log "Signal 11"; 3 kits, Codex l4 twice).  Opt-in: nets the ECO creates or touches are estimated from
# placement while repairing (every existing net keeps its routed RCX SPEF, re-read after each estimate as before); the
# legalized result is routed by the same incremental GRT + DRT and signed off on its own RCX, so no check changes.
# FLOW-25 11-03 (RSZ-0074 class, default on): a seed that carries routed data wires (OT_PRD_FROM=route|final, or a grt
# pass whose seed is a route-keeping pass's 5_1_grt.odb) is not routed by GRT: nets with wires are skipped (n3_turn i2t:
# 390 of 45721 routed; KV pcf: 0).  With the GRT source repair_design still builds a BufferedNet tree from GRT's routes
# for EVERY driver it visits, violating or not, and those routes do not match the pins:
#   no route for the net (n3_turn _172_): driver alone in its GCell = nullptr + silent Steiner fallback; driver sharing
#     GCell and layer with some loads = partial tree = RSZ-0074 "found route to 1 pins, expected 2";
#   route rebuilt from the guides in the DB (KV pcf net4170): the M1 stub ends one GCell from the pin's on-grid position
#     of this session = RSZ-0074 "found route to 36 pins, expected 37", deterministic on that DB.
# Raw run_prd.log counts, 7 days, 4 hosts, scratch copies not deduplicated: 15 of 479 wired/mixed sessions, 0 of 72 fresh.
# Such a seed therefore always repairs on the placement source above: Steiner trees, no GRT tree is built, existing nets
# keep the routed SPEF.  OT_PRD_REPAIR_RC=grt keeps the GRT source (A/B only).  Fresh seeds, checks and margins unchanged.
proc ot_prd_wired_data_nets {} {
  set clk [dict create]
  foreach n [ot_clk_dbnets] { dict set clk [$n getName] 1 }
  set wired 0
  foreach n [[ord::get_db_block] getNets] {
    if {[$n getSigType] in {POWER GROUND CLOCK} || [$n isSpecial] || [dict exists $clk [$n getName]]} continue
    set w [$n getWire]
    if {$w ne "NULL" && $w ne ""} { incr wired }
  }
  return $wired
}
set ::ot_prd_rc_place 0
set _rc [expr {[info exists ::env(OT_PRD_REPAIR_RC)] ? $::env(OT_PRD_REPAIR_RC) : ""}]
if {$_rc ni {"" placement grt}} { error "OT_PRD_REPAIR_RC=$_rc: want placement|grt" }
if {$_rc eq ""} {
  set _wired [ot_prd_wired_data_nets]
  puts "OT_PRD seed: $_wired data nets carry routed wires"
  if {$_wired > 0} {
    if {[llength [info commands ::ot_prd_native_estimate]]} {
      set _rc placement
    } else {
      puts "OT_PRD WARNING: wired seed on the frozen-clock RC path keeps the GRT repair source (RSZ-0074 possible)"
    }
  }
}
if {$_rc eq "placement"} {
  if {![llength [info commands ::ot_prd_native_estimate]]} {
    error "OT_PRD_REPAIR_RC=placement needs the routed-SPEF estimate wrapper (not the frozen-clock RC path)"
  }
  set ::ot_prd_rc_place 1
  estimate_parasitics -placement
  puts "OT_PRD repair RC: placement estimate for ECO-touched nets, routed SPEF for the rest (no GRT/PA updates in repair)"
}
global_route -start_incremental
# OT_PRD_UNFOLD_CHAINS=1: a placed input-port buffer chain can fold far away from a sink that sits at the pin
# (S81 bksel_c f_s_n[998]: flop 10 um from its pin, two buffers 100 um away, 217 um of wire, TT -19.13; repair_timing
# neither moves nor removes them).  Put the buffers of such a chain back on the pin-to-sink line, inside this GRT
# session so their nets are rerouted; detailed_placement below legalizes.  Single-sink chains of unfixed buffers only.
proc ot_prd_unfold_input_chains {} {
  set moved 0
  foreach bt [[ord::get_db_block] getBTerms] {
    if {[$bt getIoType] ne "INPUT" || [$bt getSigType] ne "SIGNAL"} continue
    set bb [$bt getBBox]
    set px [$bb xMin]; set py [$bb yMin]
    set net [$bt getNet]; set lx $px; set ly $py; set sum 0; set bufs {}; set sink ""
    while {1} {
      set inputs {}
      foreach x [$net getITerms] { if {[$x isInputSignal]} { lappend inputs $x } }
      if {[llength $inputs] != 1} { set sink ""; break }
      set inst [[lindex $inputs 0] getInst]
      lassign [$inst getLocation] ix iy
      incr sum [expr {abs($ix-$lx)+abs($iy-$ly)}]
      set lx $ix; set ly $iy
      if {![string match BUF* [[$inst getMaster] getName]]} { set sink $inst; break }
      if {[$inst isFixed]} { set sink ""; break }
      lappend bufs $inst
      set net ""
      foreach z [$inst getITerms] { if {[$z isOutputSignal]} { set net [$z getNet] } }
      if {$net eq "" || $net eq "NULL"} { set sink ""; break }
    }
    if {$sink eq "" || ![llength $bufs]} continue
    set direct [expr {abs($lx-$px)+abs($ly-$py)}]
    set um [[ord::get_db_block] getDbUnitsPerMicron]
    if {$sum <= 3*$direct + 50*$um} continue
    set n [expr {[llength $bufs]+1}]; set k 0
    foreach b $bufs {
      incr k
      $b setLocation [expr {$px+($lx-$px)*$k/$n}] [expr {$py+($ly-$py)*$k/$n}]
    }
    incr moved
    puts "OT_PRD unfold [$bt getName]: [llength $bufs] buffers, chain [expr {$sum/$um}] um, direct [expr {$direct/$um}] um"
  }
  puts "OT_PRD unfold: $moved input chains moved"
}
if {[info exists ::env(OT_PRD_UNFOLD_CHAINS)] && $::env(OT_PRD_UNFOLD_CHAINS) eq "1"} { ot_prd_unfold_input_chains }
if {[info exists ::env(OT_PRD_LOCAL_BRANCHES)] && $::env(OT_PRD_LOCAL_BRANCHES) ne ""} { source [file join $_here prd_local_branches.tcl] }
set _pass [expr {[info exists ::env(OT_PRD_PASS)] ? $::env(OT_PRD_PASS) : 1}]

# instances on clock nets (as ot_clk_freeze): drivers = clock-tree cells (dont_touch there), the rest = sinks
proc ot_prd_clock_insts {} {
  set masters [dict create]
  foreach n [ot_clk_dbnets] {
    foreach it [$n getITerms] {
      set i [$it getInst]
      dict set masters [$i getName] [[$i getMaster] getName]
    }
  }
  return $masters
}
# ASAP7 drive-strength family of a master: DFFHQNx1_ASAP7_75t_R -> DFFHQNx*_ASAP7_75t_R (one pattern per family)
proc ot_prd_family {m} {
  if {[regsub {x[0-9][0-9A-Za-z]*(_ASAP7_.*)$} $m {x*\1} f]} { return $f }
  return $m
}
set ::ot_prd_masters [ot_prd_clock_insts]
set _fams [dict create]
dict for {i m} $::ot_prd_masters {
  set inst [[ord::get_db_block] findInst $i]
  if {[$inst isDoNotTouch]} continue
  # a buffer / inverter / hold-cell family stays usable (repair needs it); such a sink is covered by the revert guard
  if {[regexp {^(BUF|INV|HB[0-9]|CKINV)} $m]} continue
  dict set _fams [ot_prd_family $m] 1
}
set _du 0
foreach f [lsort [dict keys $_fams]] {
  set lc [get_lib_cells -quiet */$f]
  if {[llength $lc]} { set_dont_use $lc; incr _du [llength $lc] }
}
puts "OT_PRD pass $_pass sink guard: [dict size $::ot_prd_masters] clock-net instances, [dict size $_fams] sink master families -> set_dont_use $_du lib cells for the ECO session: [lsort [dict keys $_fams]]"

# KW-FIX-18 11-05: OT_MAX_FANOUT is optional (absent/empty = 0, no cap); prd_run.sh always passes it
set _mfo [expr {[info exists ::env(OT_MAX_FANOUT)] && $::env(OT_MAX_FANOUT) ne "" ? $::env(OT_MAX_FANOUT) : 0}]
if {$_mfo > 0} { set_max_fanout $_mfo [current_design] }
puts "OT_PRD pass $_pass repair_design slew_margin $::env(OT_SLEW_MARGIN) cap_margin $::env(OT_SLEW_MARGIN) max_fanout $_mfo (routed RCX SPEF)"
set _drv_args [list -slew_margin $::env(OT_SLEW_MARGIN) -cap_margin $::env(OT_SLEW_MARGIN)]
# Optional geometric data-net segmentation, independent of the Liberty slew
# repair decision. Frozen clock nets/drivers remain protected by ot_clk_freeze.
set _wire_limit [expr {[info exists ::env(OT_PRD_MAX_WIRE_LENGTH)] ? $::env(OT_PRD_MAX_WIRE_LENGTH) : 0}]
if {![string is double -strict $_wire_limit] || $_wire_limit < 0} {error "OT_PRD invalid max wire length $_wire_limit"}
if {$_wire_limit > 0} {lappend _drv_args -max_wire_length $_wire_limit}
puts "OT_PRD pass $_pass repair_design $_drv_args"
# KW-FIX-17 11-05: targeted fanout cap on violator nets above OT_PRD_AUTO_FANOUT loads (default 32; prd_autofo.tcl)
set _afo [expr {[info exists ::env(OT_PRD_AUTO_FANOUT)] && $::env(OT_PRD_AUTO_FANOUT) ne "" ? $::env(OT_PRD_AUTO_FANOUT) : 32}]
set _tfo [expr {[info exists ::env(OT_PRD_TARGET_FANOUT)] && $::env(OT_PRD_TARGET_FANOUT) ne "" ? $::env(OT_PRD_TARGET_FANOUT) : 0}]
if {[info exists _here] && ([info exists ::env(OT_MAX_FANOUT)] && $::env(OT_MAX_FANOUT) ne "" ? $::env(OT_MAX_FANOUT) : 0) == 0 && $_tfo == 0 && $_afo ne "0" && [file exists [file join $_here prd_autofo.tcl]]} {
  source [file join $_here prd_autofo.tcl]
  ot_prd_auto_fanout $_drv_args $_afo
}
if {[info exists ::env(OT_PRD_TARGETED)] && $::env(OT_PRD_TARGETED) eq "1"} {
  source [file join $_here prd_targeted.tcl]
  ot_prd_repair_targeted $_drv_args
} else {
  repair_design {*}${_drv_args}
}
if {$::env(OT_SETUP_MARGIN) ne ""} {
  # DIE-S81-49 11-02 (class fix, removed-buffer class): an UnbufferMove deletes an instance inside the incremental-GRT
  # session; GRT/DRT then touch the deleted cell -- SIGSEGV in drt::FlexPA (getEdgeCost / FlexGCWorker::initPA0, at the
  # first repair move or at global_route -end_incremental with OT_PRD_REPAIR_RC=placement) or GRT-0228 usage=65535
  # (edge usage decremented below 0).  Measured: every crashed S81 ECO (l1c A/B, caprt, XRT1 w80/w60, H0 i2) removed or
  # was removing a buffer; every completed one (H0 i1, BF i1t) removed none.  The ECO keeps sizing / buffering /
  # cloning / pin swaps; OT_PRD_BUFFER_REMOVAL=1 restores the old move set.  No check or margin change.
  set _st_args [list -setup -setup_margin $::env(OT_SETUP_MARGIN) -skip_last_gasp]
  if {![info exists ::env(OT_PRD_BUFFER_REMOVAL)] || $::env(OT_PRD_BUFFER_REMOVAL) ne "1"} { lappend _st_args -skip_buffer_removal }
  puts "OT_PRD pass $_pass repair_timing $_st_args"
  repair_timing {*}$_st_args
}
# KW-FIX-24 11-06 (COORD 13:2x item 4): OT_HOLD_REPAIR_SCOPE=reg2reg (HOLD-REPAIR-SCOPE, orfs_hold_mm.tcl
# ot_hold_repair_scope) now also scopes this post-route hold repair: port hold is the parent's (io_hold_parent), so no
# buffer budget is spent on the standalone IO frame.  Two-mode session (kit_modes_eco.tcl synced, stage 4_cts.sdc): the
# shared ot_hold_repair_scope itself.  Single-mode session (no orfs_hold_mm): the same temporary -hold false paths from
# the non-clock inputs / to the outputs around the repair, then the exact SDC replay + write-back compare of that proc.
# OWNER 11-07: nonport excludes only input-port starts; register-to-output and macro/internal hold remains core work.
# Env unset (or any other value): the body runs exactly as before. Legacy reg2reg semantics are unchanged.
proc ot_prd_hold_scope {body} {
  if {[info exists ::ot_prd_expected_hold_scope] &&
      (![info exists ::env(OT_HOLD_REPAIR_SCOPE)] || $::env(OT_HOLD_REPAIR_SCOPE) ne $::ot_prd_expected_hold_scope)} {
    error "OT_HOLD_SCOPE expected $::ot_prd_expected_hold_scope in actual OpenROAD environment; refusing unscoped repair"
  }
  if {![info exists ::env(OT_HOLD_REPAIR_SCOPE)] || $::env(OT_HOLD_REPAIR_SCOPE) ni {reg2reg nonport}} {
    return [uplevel 1 $body]
  }
  set scope $::env(OT_HOLD_REPAIR_SCOPE)
  set mm_active [expr {[info exists ::ot_mm_active] && $::ot_mm_active}]
  set mm_synced [expr {[info exists ::ot_mm_synced] && $::ot_mm_synced}]
  set mm_stage [expr {[info exists ::ot_mm_stage] ? $::ot_mm_stage : "UNSET"}]
  puts "OT_PRD_HOLD_SCOPE requested=$scope mm_active=$mm_active mm_synced=$mm_synced stage=$mm_stage"
  if {$mm_active} {
    # The shared helper returns BODY unscoped outside this exact FF context.
    # A late ECO must refuse that path, never silently pad the parent's ports.
    if {!$mm_synced || $mm_stage ne "4_cts.sdc" || ![llength [info commands ot_hold_repair_scope]]} {
      error "OT_HOLD_SCOPE refusing unscoped late repair: scope=$scope active=$mm_active synced=$mm_synced stage=$mm_stage; establish the validated FF scene first"
    }
    if {![info exists ::ot_hold_scope_supported_modes] || $scope ni $::ot_hold_scope_supported_modes} {
      error "OT_HOLD_SCOPE $scope requires matching orfs_hold_mm.tcl; refusing unscoped repair"
    }
    puts "OT_PRD hold scope $scope: shared ot_hold_repair_scope (orfs_hold_mm.tcl)"
    set ::ot_prd_scope_entered 1
    set result [uplevel 1 [list ot_hold_repair_scope $body]]
    set ::ot_prd_scope_restored 1
    set ::ot_prd_scope_completed 1
    puts "OT_PRD_HOLD_SCOPE_COMPLETE scope=$scope mode=ff"
    return $result
  }
  set dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : [pwd]}]
  set stem [file join $dir ot_prd_hold_scope_[pid]_[clock clicks]]
  set before ${stem}_before.sdc
  set after ${stem}_after.sdc
  write_sdc -digits 17 -no_timestamp $before
  set clock_sources [dict create]
  foreach clock [all_clocks] {
    foreach source [get_property $clock sources] { dict set clock_sources [get_full_name $source] 1 }
  }
  set inputs {}
  foreach port [all_inputs] {
    if {![dict exists $clock_sources [get_full_name $port]]} { lappend inputs $port }
  }
  set outputs {}
  if {$scope eq "reg2reg"} { set outputs [all_outputs] }
  puts "OT_HOLD_SCOPE begin (post-route single-mode) scope=$scope input_ports=[llength $inputs] excluded_output_ports=[llength $outputs]"
  set completed 0
  try {
    if {[llength $inputs]} { set_false_path -hold -from $inputs }
    if {[llength $outputs]} { set_false_path -hold -to $outputs }
    puts "OT_HOLD_SCOPE repair scope=$scope (nonport retains register-to-output and macro/internal paths)"
    set ::ot_prd_scope_entered 1
    set result [uplevel 1 $body]
    set completed 1
    return $result
  } finally {
    if {[llength $inputs]} { unset_path_exceptions -hold -from $inputs }
    if {[llength $outputs]} { unset_path_exceptions -hold -to $outputs }
    read_sdc $before
    write_sdc -digits 17 -no_timestamp $after
    set fb [open $before r]; set tb [read $fb]; close $fb
    set fa [open $after r]; set ta [read $fa]; close $fa
    if {$tb ne $ta} { error "OT_HOLD_SCOPE restore differs: retained $before $after" }
    set ::ot_prd_scope_restored 1
    if {$completed} {
      set ::ot_prd_scope_completed 1
      puts "OT_PRD_HOLD_SCOPE_COMPLETE scope=$scope mode=single"
    }
    puts "OT_HOLD_SCOPE restored exact SDC (port hold remains visible)"
    if {![info exists ::env(OT_HOLD_SCOPE_KEEP_SDC)] || $::env(OT_HOLD_SCOPE_KEEP_SDC) ne "1"} {
      file delete $before $after
    }
  }
}
proc ot_prd_hold_scope_assert {} {
  if {[info exists ::env(OT_PRD_NO_HOLD)] && $::env(OT_PRD_NO_HOLD) eq "1"} { return }
  set requested [expr {[info exists ::ot_prd_expected_hold_scope] ? $::ot_prd_expected_hold_scope :
                       ([info exists ::env(OT_HOLD_REPAIR_SCOPE)] ? $::env(OT_HOLD_REPAIR_SCOPE) : "")}]
  if {$requested ni {reg2reg nonport}} { return }
  foreach flag {ot_prd_scope_entered ot_prd_scope_restored ot_prd_scope_completed} {
    if {![info exists ::$flag] || ![set ::$flag]} {
      error "OT_HOLD_SCOPE missing runtime $flag for requested $requested; refusing route after unobserved scoped repair"
    }
  }
  puts "OT_PRD_HOLD_SCOPE_VERIFIED scope=$requested entered=1 restored=1 completed=1"
}
set ::ot_prd_scope_entered 0
set ::ot_prd_scope_restored 0
set ::ot_prd_scope_completed 0
set args [list -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)]
if {$::env(OT_HOLD_ALLOW_SETUP) == 1} { lappend args -allow_setup_violations }
# two-mode kits: the SHARED guarded hold repair of orfs_hold_mm.tcl (R5 chunk buffer cap inside the same total budget,
# met-first, stall + time limits, FF clock RC calibration) -- R7 KV canary: one raw call sat >30 min in iteration 0 on
# 9,048 margin endpoints at real ws -10.5 (the E0 plateau class).  Kits without the session keep the raw call.
if {[info exists ::env(OT_PRD_NO_HOLD)] && $::env(OT_PRD_NO_HOLD) eq "1"} {
  # KW-ECO-1 variant t<N> (TT-only single-mode pass): setup + DRV only; hold is repaired in the FF-only b<N> pass
  puts "OT_PRD pass $_pass hold: skipped (OT_PRD_NO_HOLD=1, TT-only pass)"
} elseif {[llength [info commands ot_repair_hold_guarded]] && [ot_hold_guard_on]} {
  puts "OT_PRD pass $_pass hold: shared guarded repair (orfs_hold_mm.tcl) $args"
  ot_rc_cal_hold { ot_prd_hold_scope { ot_repair_hold_guarded $args } }
} else {
  puts "OT_PRD pass $_pass repair_timing -hold $args"
  ot_prd_hold_scope { repair_timing -hold {*}$args }
}
# Verify the entire RC-calibration dispatch too: its callback must really have run.
ot_prd_hold_scope_assert

# fail-safe: any clock-net instance whose master changed is put back (LOCKED cells are never legalized, so a grown
# master overlaps its neighbours); the count is reported, a revert that cannot be applied stops the ECO
proc ot_prd_sink_revert {} {
  set block [ord::get_db_block]
  set rev {}
  dict for {i m} $::ot_prd_masters {
    set inst [$block findInst $i]
    if {$inst eq "NULL" || $inst eq ""} { error "OT_PRD FAIL: clock-net instance $i vanished in the ECO" }
    set now [[$inst getMaster] getName]
    if {$now ne $m} {
      if {[catch {replace_cell [get_cells -quiet $i] [lindex [get_lib_cells */$m] 0]} msg]} {
        error "OT_PRD FAIL: cannot restore $i $now -> $m: $msg"
      }
      if {[[$inst getMaster] getName] ne $m} { error "OT_PRD FAIL: $i still $now after restore" }
      lappend rev "$i:$now->$m"
    }
  }
  puts "OT_PRD sink guard: [llength $rev] clock-net instance masters restored [lrange $rev 0 19]"
  return [llength $rev]
}
ot_prd_dtoff_restore
set ::ot_prd_reverted [ot_prd_sink_revert]
# OT_PAD_MASTERS as eco_route.tcl (DRT pin access around abutted ECO buffers)
if {[info exists ::env(OT_PAD_MASTERS)] && $::env(OT_PAD_MASTERS) ne ""} {
  foreach mp $::env(OT_PAD_MASTERS) {
    lassign [split $mp :] m n
    set_placement_padding -masters [list $m] -left $n -right $n
  }
}
detailed_placement
# KW-FIX-17 11-05 (DPL-0033 class, COORD 14:52 / HBM-FORM-TIMING-6 14:55, default-on): when the ECO legalization leaves
# overlaps (pcol_s3 ECO i1: DPL-0033, 33 overlaps), run the diamond legalizer once and re-check before failing.  The
# same block let pcol_s3b pass legalization (lane copy, prd_hook.tcl sha 05a165647b00).  OT_PRD_DIAMOND_FALLBACK=0 = off.
if {[catch {check_placement} msg]} {
  if {[info exists ::env(OT_PRD_DIAMOND_FALLBACK)] && $::env(OT_PRD_DIAMOND_FALLBACK) eq "0"} {
    error "OT_PRD FAIL: check_placement after the ECO legalization: $msg"
  }
  puts "OT_PRD legalizer fallback: diamond after: $msg"
  detailed_placement -use_diamond_legalizer
  if {[catch {check_placement} msg]} { error "OT_PRD FAIL: check_placement after the ECO legalization: $msg" }
}
if {[info exists ::ot_prd_local_sequential]} {ot_prd_local_sequential_audit}
# FLOW-12 opt-in OT_PRD_FROM=route (prd_mk.sh): the ECO started from the ROUTED DB -> rip only the nets it touched,
# keep every other net's routed wires for an incremental detailed route (prd_route_keep.tcl).  FLOW-13: selection + rip
# run BEFORE the incremental GRT end and the kept wires are parked (detached) across it, since updateDirtyNets destroys
# the wire of every journaled-dirty net (R1route: 2754 reference wires lost, 0 ripped).
if {[llength [info commands ot_prd_tie_mark_dirty]]} { ot_prd_tie_mark_dirty }
set _route_keep [expr {[info exists ::env(OT_PRD_FROM)] && $::env(OT_PRD_FROM) in {route final}}]
if {$_route_keep} {
  source [file join $_here prd_route_keep.tcl]
  ot_prd_route_keep
}
set ::ot_prd_rc_place 0
global_route -end_incremental
ot_clk_freeze_assert post_grt
if {$_route_keep} { ot_prd_route_keep_restore }
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
puts "OT_PRD pass $_pass hook done (sink masters restored $::ot_prd_reverted)"
