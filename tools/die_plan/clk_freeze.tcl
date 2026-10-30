# FLOW-CLKFREEZE 2026-10-27 (COORD ruling HEAD-CORE-R19 (1)): lock the routed clock network through every post-route
# ECO (repair_design / repair_timing / detailed_placement / incremental GRT / DRT), shared by all dies' ECO hooks
# (tools/s81_head/head_eco_post.tcl, physical/die_plan/qwen_kvsys/cores/harden/eco/eco_route.tcl,
#  physical/die_plan/qwen_compute/cores/legacy/hold_route.tcl).
#
# Root cause (CHECKED on HEAD elemA r19_residual3, see tools/die_plan/clk_geom_diff.py): the ECO re-routes clock
# nets in two places, neither stopped by 'dont_touch' (which is an rsz-only attribute):
#   (1) global_route -end_incremental destroys the dbWire of every DIRTY net (GlobalRouter::updateDirtyNets ->
#       destroyNetWire) and re-routes it; a clock net turns dirty when any instance on it moves (detailed_placement
#       legalising the new hold buffers shifts sink flops / clock cells) or changes master;
#   (2) detailed_route keeps an existing ROUTED wire only in its INCR iterations; DRC-mode iterations rip up any
#       non-FIXED net near a marker (FlexDRWorker::canRipup), so clock leaf nets next to new data wires are re-routed.
# OpenROAD's supported lock is the FIXED wire type: DRT reads a FIXED dbWire as frNet::isFixed (never ripped up,
# never rewritten by io::Writer::updateDb), GRT skips any net that has a wire (Net::hasWires).  The lock below
#   a) re-encodes every clock net's dbWire with wire type FIXED (opcode stream otherwise byte-identical: verified);
#   b) freezes every instance on a clock net (clock buffers / inverters / ICGs and the sink flops / macros):
#      placement status LOCKED = DEF FIXED (detailed_placement cannot move it, so GRT never marks the clock net dirty) and
#      dont_touch (rsz cannot resize it: sink clock-pin cap and driver strength stay as signed);
#   c) sets dont_touch on the clock nets (no rsz buffering / removal).
# Hold / setup repair keeps every data-path move (HB4 insertion on D pins, data-cell sizing, data buffering).
# The blocking check is separate: ot_clk_dump before the ECO + after the route, tools/die_plan/clk_geom_diff.py.
#
# Env: OT_CLK_FREEZE (default 1; 0 = dump only, NO lock -- diagnostic baseline, logged as such).

proc ot_clk_dbnets {} {
  # clock network = nets with sig type CLOCK (CTS / plan-built trees) UNION the STA clock network (same set GRT uses)
  set block [ord::get_db_block]
  set nets [dict create]
  foreach net [$block getNets] {
    if {[$net getSigType] eq "CLOCK"} { dict set nets [$net getName] $net }
  }
  if {[llength [info commands sta::find_all_clk_nets]] && [llength [sta::all_clocks]]} {
    if {![catch {sta::find_all_clk_nets} sn]} {
      foreach n $sn {
        # this OpenROAD returns odb dbNet handles; older builds return STA nets
        if {[string match "*odb__dbNet*" $n]} {
          set dn $n
        } elseif {[catch {$block findNet [get_full_name $n]} dn]} {
          continue
        }
        if {$dn ne "NULL" && $dn ne ""} { dict set nets [$dn getName] $dn }
      }
    }
  }
  set out {}
  foreach k [lsort [dict keys $nets]] {
    set n [dict get $nets $k]
    if {[$n getSigType] in {POWER GROUND}} continue
    lappend out $n
  }
  return $out
}

# raw opcode stream of a wire with the wire-type bits (0xE0) of PATH/SHORT/JUNCTION/VWIRE ops masked and ITERM/BTERM
# ids resolved to names: identical geometry + connectivity <=> identical token list
proc ot_clk_wire_tokens {net} {
  set w [$net getWire]
  if {$w eq "NULL" || $w eq ""} { return {} }
  set block [$net getBlock]
  set toks {}
  set n [$w length]
  for {set i 0} {$i < $n} {incr i} {
    set op [$w getOpcode $i]
    set d [$w getData $i]
    set code [expr {$op & 0x1F}]
    if {$code in {0 1 2 13}} { set op [expr {$op & 0x1F}] }
    if {$code == 9} {
      set it [odb::dbITerm_getITerm $block $d]
      set d "[[$it getInst] getName]/[[$it getMTerm] getName]"
    } elseif {$code == 10} {
      set d [[odb::dbBTerm_getBTerm $block $d] getName]
    } elseif {$code == 0} {
      set d [[odb::dbTechLayer_getTechLayer [[$block getDb] getTech] $d] getName]
    } elseif {$code == 7} {
      set d "V:[[odb::dbVia_getVia $block $d] getName]"
    } elseif {$code == 8} {
      set d "TV:[[odb::dbTechVia_getTechVia [[$block getDb] getTech] $d] getName]"
    }
    lappend toks "$op:$d"
  }
  return $toks
}

proc ot_clk_wire_types {net} {
  # set of wire types used by the PATH-class ops (0x40 FIXED, 0x60 ROUTED)
  set w [$net getWire]
  set t {}
  if {$w eq "NULL" || $w eq ""} { return $t }
  set n [$w length]
  for {set i 0} {$i < $n} {incr i} {
    set op [$w getOpcode $i]
    if {($op & 0x1F) in {0 1 2 13}} { lappend t [expr {$op & 0xE0}] }
  }
  return [lsort -unique $t]
}

# dump: one NET line per clock net (point count, wire types, tokens), one PIN line per iterm, one INST line per instance on a clock net.
# nets_file (optional): also dump these net names (the pre-ECO set), so a vanished / split net is reported.
proc ot_clk_dump {path {tag ""} {nets_file ""}} {
  set block [ord::get_db_block]
  set nets [dict create]
  foreach n [ot_clk_dbnets] { dict set nets [$n getName] $n }
  if {$nets_file ne "" && [file exists $nets_file]} {
    set fh [open $nets_file r]
    foreach nm [split [read $fh] "\n"] {
      if {$nm eq "" || [dict exists $nets $nm]} continue
      set dn [$block findNet $nm]
      dict set nets $nm $dn
    }
    close $fh
  }
  set fo [open $path w]
  puts $fo "#CLKDUMP tag $tag nets [dict size $nets] block [$block getName]"
  set insts [dict create]
  set t0 [clock milliseconds]
  foreach nm [lsort [dict keys $nets]] {
    set n [dict get $nets $nm]
    if {$n eq "NULL" || $n eq ""} { puts $fo "MISSING\t$nm"; continue }
    set w [$n getWire]
    set len 0
    if {$w ne "NULL" && $w ne ""} { set len [$w count] }
    puts $fo "NET\t$nm\t[$n getSigType]\t$len\t[join [ot_clk_wire_types $n] ,]\t[join [ot_clk_wire_tokens $n] { }]"
    set pins {}
    foreach it [$n getITerms] {
      set inst [$it getInst]
      lappend pins "[$inst getName]/[[$it getMTerm] getName]"
      dict set insts [$inst getName] $inst
    }
    foreach bt [$n getBTerms] { lappend pins "PORT:[$bt getName]" }
    puts $fo "PIN\t$nm\t[join [lsort $pins] { }]"
  }
  foreach k [lsort [dict keys $insts]] {
    set i [dict get $insts $k]
    lassign [$i getLocation] x y
    puts $fo "INST\t$k\t[[$i getMaster] getName]\t$x\t$y\t[$i getOrient]\t[$i getPlacementStatus]"
  }
  close $fo
  puts [format "OT_CLK_DUMP %s %s nets %d insts %d %.1f s" $tag $path [dict size $nets] [dict size $insts] \
    [expr {([clock milliseconds] - $t0) / 1000.0}]]
}

# decode one net's wire into an encoder op list (wire type forced FIXED); [] when the net has no wire
proc ot_clk_wire_ops {net} {
  set w [$net getWire]
  if {$w eq "NULL" || $w eq ""} { return {} }
  set ops {}
  set dec [odb::dbWireDecoder]
  $dec begin $w
  set END $odb::dbWireDecoder_END_DECODE
  while {1} {
    set op [$dec next]
    if {$op == $END} break
    switch $op {
      0 - 1 - 2 - 3 {
        # PATH / JUNCTION / SHORT / VWIRE (+ optional RULE op right after)
        # Capture the PATH/JUNCTION operands before consuming optional RULE:
        # decoder.next changes its current operand to the layer-rule ID.
        set rule ""
        switch $op {
          0 { set a [list newPath [$dec getLayer] FIXED] }
          1 { set a [list newPath [$dec getJunctionValue] FIXED] }
          2 { set a [list newPathShort [$dec getJunctionValue] [$dec getLayer] FIXED] }
          3 { set a [list newPathVirtualWire [$dec getJunctionValue] [$dec getLayer] FIXED] }
        }
        if {[$dec peek] == 11} { $dec next; set rule [$dec getRule] }
        if {$op == 1} {
          # newPath(junction) already emits the following colinear point.
          # Re-emitting it with addPoint shifts every later junction index.
          # Preserve an extension with newPathExt instead of adding a point.
          set point_op [$dec next]
          if {$point_op == 5} {
            set a [list newPathExt [lindex $a 1] [lindex [$dec getPoint_ext] 2] FIXED]
          } elseif {$point_op != 4} {
            error "OT_CLK_FREEZE FAIL: junction lacks its initial point in [$net getName]"
          }
        }
        if {$rule ne ""} { lappend a $rule }
        lappend ops $a
      }
      4 { lappend ops [list addPoint {*}[lrange [$dec getPoint] 0 1]] }
      5 { lappend ops [list addPoint {*}[lrange [$dec getPoint_ext] 0 2]] }
      6 { lappend ops [list addVia [$dec getVia]] }
      7 { lappend ops [list addTechVia [$dec getTechVia]] }
      8 {
        # RECT: operands = kRect + 3 kOperand at the op index (decoder has no Tcl getter for the deltas)
        set j [$dec getJunctionId]
        lappend ops [list addRect [$w getData $j] [$w getData [expr {$j+1}]] [$w getData [expr {$j+2}]] [$w getData [expr {$j+3}]]]
      }
      9 { lappend ops [list addITerm [$dec getITerm]] }
      10 { lappend ops [list addBTerm [$dec getBTerm]] }
      11 { error "OT_CLK_FREEZE FAIL: stray RULE op in [$net getName]" }
      default { error "OT_CLK_FREEZE FAIL: unsupported wire op $op in [$net getName]" }
    }
  }
  # Read raw property operands. Decoder getProperty is undefined for the
  # first point; raw positions also preserve the exact existing wire encoding.
  for {set i 0} {$i < [$w length]} {incr i} {
    if {([$w getOpcode $i] & 0x1F) != 12 || [$w getData $i] == 0} continue
    set junction [expr {$i - 1}]
    if {([$w getOpcode $junction] & 0x1F) ni {4 5}} { incr junction -1 }
    if {$junction < 0 || ([$w getOpcode $junction] & 0x1F) ni {4 5}} {
      error "OT_CLK_FREEZE FAIL: unsupported property operand at $i"
    }
    lappend ops [list wireProperty $junction [$w getData $i]]
  }
  return $ops
}

# encode OPS as the net's new (FIXED) wire, replacing any current wire; the result must reproduce TOKENS exactly
# (fail closed: the ECO must not run, or continue, on a half-locked clock)
proc ot_clk_encode_wire {net ops tokens} {
  set nw [odb::dbWire_create [$net getBlock]]
  set enc [odb::dbWireEncoder]
  $enc begin $nw
  set properties {}
  foreach a $ops {
    if {[lindex $a 0] eq "wireProperty"} {
      lappend properties [lrange $a 1 2]
    } else {
      $enc {*}$a
    }
  }
  $enc end
  # RCX junction metadata defaults to zero in the encoder. Restore it with
  # the supported dbWire API, then require the SAME complete token stream.
  foreach pair $properties {
    lassign $pair junction property
    if {![$nw setProperty $junction $property]} {
      error "OT_CLK_FREEZE FAIL: cannot preserve point property at $junction"
    }
  }
  set w [$net getWire]
  if {$w ne "NULL" && $w ne ""} { odb::dbWire_destroy $w }
  $nw attach $net
  if {[ot_clk_wire_tokens $net] ne $tokens || [ot_clk_wire_types $net] ne {64}} {
    error "OT_CLK_FREEZE FAIL: FIXED encode of [$net getName] is not byte-identical to the routed wire"
  }
}

# re-encode one net's wire with wire type FIXED; returns 1 if changed, 0 if already FIXED / no wire.  Keeps the op list
# + tokens in ::ot_clk_ops / ::ot_clk_tok for ot_clk_freeze_assert's restore.
proc ot_clk_fix_wire {net} {
  set w [$net getWire]
  if {$w eq "NULL" || $w eq ""} { return 0 }
  set nm [$net getName]
  set before [ot_clk_wire_tokens $net]
  set ops [ot_clk_wire_ops $net]
  set n0 [$w length]
  set ::ot_clk_ops($nm) $ops
  set ::ot_clk_tok($nm) $before
  if {[ot_clk_wire_types $net] eq {64}} { return 0 }
  ot_clk_encode_wire $net $ops $before
  if {[[$net getWire] length] != $n0} { error "OT_CLK_FREEZE FAIL: FIXED re-encode of [$net getName] is not byte-identical (ops $n0 -> [[$net getWire] length])" }
  return 1
}

proc ot_clk_freeze {{dump_dir ""}} {
  if {$dump_dir eq ""} { set dump_dir $::env(RESULTS_DIR) }
  set mode [expr {[info exists ::env(OT_CLK_FREEZE)] ? $::env(OT_CLK_FREEZE) : 1}]
  set nets [ot_clk_dbnets]
  set fh [open $dump_dir/clk_freeze_nets.txt w]
  foreach n $nets { puts $fh [$n getName] }
  close $fh
  ot_clk_dump $dump_dir/clk_freeze_pre.tsv pre
  if {$mode != 1} {
    puts "OT_CLK_FREEZE OFF (OT_CLK_FREEZE=$mode): clock nets NOT locked -- diagnostic baseline only, never a sign-off route"
    set ::ot_clk_frozen 0
    return
  }
  set nfix 0; set nwire 0; set insts [dict create]; set drv [dict create]
  array unset ::ot_clk_ops; array unset ::ot_clk_tok
  foreach n $nets {
    if {[$n getWire] ne "NULL" && [$n getWire] ne ""} { incr nwire }
    incr nfix [ot_clk_fix_wire $n]
    $n setDoNotTouch 1
    foreach it [$n getITerms] {
      dict set insts [[$it getInst] getName] [$it getInst]
      if {[$it isOutputSignal]} { dict set drv [[$it getInst] getName] 1 }
    }
  }
  set nmoved 0; set ndt 0
  foreach k [dict keys $insts] {
    set i [dict get $insts $k]
    # odb LOCKED = DEF FIXED (DPL / rsz never move LOCKED, FIRM or COVER instances)
    if {[$i getPlacementStatus] ni {FIRM LOCKED COVER}} {
      incr nmoved
      $i setPlacementStatus LOCKED
    }
    # dont_touch only on clock-tree cells (an output pin on a clock net); sink flops stay touchable so hold repair can
    # insert buffers before their D pins (dont_touch sinks -> RSZ-3006, HEAD canary 10-27 11:57).  A sink resize would
    # change the clock-net pin geometry -> caught by the blocking check (inst master diff).
    if {[dict exists $drv $k]} { $i setDoNotTouch 1; incr ndt }
  }
  set ::ot_clk_frozen 1
  set ::ot_clk_frozen_nets {}
  foreach n $nets { if {[$n getWire] ne "NULL" && [$n getWire] ne ""} { lappend ::ot_clk_frozen_nets [$n getName] } }
  puts "OT_CLK_FREEZE ON clock nets [llength $nets] (with wire $nwire, re-encoded FIXED $nfix) instances [dict size $insts] (placement -> LOCKED: $nmoved were movable) dont_touch nets + $ndt clock-tree cells"
}

# inside the ECO session, after each global_route -end_incremental.  OpenROAD GlobalRouter::updateDirtyNets destroys the
# dbWire of EVERY dirty net regardless of wire type (no FIXED guard; a clock net gets dirty when e.g. pin access points of
# a sink are reset next to a new hold buffer: QC canary 10-27 11:57, 20/106 nets), so the lock restores each frozen
# net's FIXED wire byte-identically from the op list taken at freeze (before DRT sees the net), then asserts every
# frozen net carries exactly its pre-ECO wire.  Restored nets are listed; the chain's clock-geometry diff stays blocking.
proc ot_clk_freeze_assert {tag} {
  if {![info exists ::ot_clk_frozen] || !$::ot_clk_frozen} { return }
  set bad {}; set restored {}
  set block [ord::get_db_block]
  foreach nm $::ot_clk_frozen_nets {
    set n [$block findNet $nm]
    if {$n eq "NULL" || $n eq ""} { lappend bad $nm; continue }
    set w [$n getWire]
    if {($w eq "NULL" || $w eq "") || [ot_clk_wire_types $n] ne {64} || [ot_clk_wire_tokens $n] ne $::ot_clk_tok($nm)} {
      if {[catch {ot_clk_encode_wire $n $::ot_clk_ops($nm) $::ot_clk_tok($nm)} msg]} { lappend bad $nm; puts $msg; continue }
      lappend restored $nm
    }
  }
  if {[llength $bad]} {
    error "OT_CLK_FREEZE FAIL $tag: [llength $bad] clock nets cannot carry their pre-ECO FIXED wire: [lrange $bad 0 19]"
  }
  puts "OT_CLK_FREEZE $tag OK: all [llength $::ot_clk_frozen_nets] clock nets carry their pre-ECO FIXED wire (restored [llength $restored] destroyed by GRT updateDirtyNets: [lrange $restored 0 19][expr {[llength $restored] > 20 ? { ...} : {}}])"
}

# Restore ORIGINAL frozen-clock parasitics after native estimate_parasitics, retaining its DATA RC in memory.
# Opt-in: callers supply a dict of exact scene/corner names to prequalified CLOCK-ONLY SPEFs, e.g.
#   ot_clk_restore_parasitics [dict create tc original_clock_only.spef BC original_clock_only.spef]
# Names are case-sensitive and must be the scenes populated by the native estimator. Clock wires/cells/masters
# must still match the original SPEF (use the existing freeze/geometry audit). This does not qualify a changed clock.
#
# Installed OpenROAD 6cb3f2b704 / OpenSTA 509913b: native global-route estimation creates one dataset per scene name.
# read_spef -corner alone REPLACES that dataset, silently losing the native DATA annotations. Explicit -name reuses
# it and replaces only the SPEF's clock nets. -increment is parsed but unused; do not substitute it for -name.
# No SPEF unit conversion, native DATA export, terminal-cap reconstruction, or coupling projection is needed.
proc ot_clk_restore_parasitics {spef_by_corner} {
  if {![dict size $spef_by_corner]} {
    error "ot_clk_restore_parasitics needs at least one exact corner/SPEF pair"
  }
  # Validate every input before any annotation changes. In particular, do not let -name silently CREATE a new
  # unbound dataset: the annotation report raises STA-1560 when the existing native dataset is absent.
  foreach {corner spef} $spef_by_corner {
    if {$corner eq "" || ![file isfile $spef] || ![file readable $spef]} {
      error "ot_clk_restore_parasitics: unreadable clock SPEF '$spef' for corner '$corner'"
    }
    report_parasitic_annotation -name $corner
  }
  foreach {corner spef} $spef_by_corner {
    read_spef -name $corner -corner $corner $spef
    puts "OT_CLK_RC_RESTORE corner $corner dataset $corner clock_spef $spef"
  }
  return [dict keys $spef_by_corner]
}
