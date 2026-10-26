# Sub-tap latency PADDING for the multi-root shallow clock (PATH-QC-N59-PAD 2026-10-25).
# Source AFTER the closed-loop trunk build + the ONE global CTS (shallow_clock_multi.tcl), in a session with a
# propagated clock and placement parasitics.  One structural mechanism: a series chain of identical delay buffers on
# each sub-tap's ROOT BRANCH (trunk leaf net -> chain -> sub-tap buffer input), sized from the measured natural
# port-referred mean sink insertion (shallow_clock_pad.py).  The trunk, the sub-tap buffers, the local CTS trees and
# every sink are untouched; the chain cells are new, PG-bound, placed beside their sub-tap and legalised once.
#
#   ::ot_dtsh_pad::run $blk $spec ?opts?
#     spec: list of {tap_inst_name kind target_tt_ps}   (kind reg|mac, report only)
#     opts dict: master (BUFx2_ASAP7_75t_R) iters (4) tol (6) default_stage (15) max_stages (16) dir (/out) pg {POWER net GROUND net}
#   -> dict tap -> {n stages, natural, mean, target}
# Env: OT_DTSH_PAD_PY overrides the sizer path.
if {[namespace exists ::ot_dtsh_pad]} { return }
namespace eval ::ot_dtsh_pad {
  variable source_dir [file dirname [file normalize [info script]]]
  variable chains {}     ;# tap -> {net <original leaf net> cells {inst ...} nets {net ...}}
  variable sinkpins {}   ;# tap -> STA sink pins (local tree below the sub-tap output; unchanged by padding)
}
proc ::ot_dtsh_pad::sigpin {inst dir} {
  set out {}
  foreach it [$inst getITerms] {
    if {[[$it getMTerm] getSigType] in {POWER GROUND}} continue
    if {[[$it getMTerm] getIoType] eq $dir} { lappend out $it }
  }
  if {[llength $out] != 1} { error "OT_DTSH_PAD [$inst getName] needs exactly one $dir signal pin" }
  return [lindex $out 0]
}
proc ::ot_dtsh_pad::local_sinks {net {depth 0}} {
  if {$depth > 40} { error "OT_DTSH_PAD local tree deeper than 40 at [$net getName]" }
  set out {}
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]; set m [$inst getMaster]
    if {![$m isBlock] && [regexp {^(BUF|INV|CKINV|CKBUF|HB)} [$m getName]]} {
      set o [sigpin $inst OUTPUT]
      if {[$o getNet] ne "NULL"} { lappend out {*}[local_sinks [$o getNet] [expr {$depth+1}]] }
      continue
    }
    lappend out "[$inst getName]/[[$it getMTerm] getName]"
  }
  return $out
}
proc ::ot_dtsh_pad::measure {blk taps} {
  variable sinkpins
  set res {}
  foreach tap $taps {
    if {![dict exists $sinkpins $tap]} {
      set inst [$blk findInst $tap]
      set pins {}
      foreach pn [local_sinks [[sigpin $inst OUTPUT] getNet]] { set p [get_pins -quiet $pn]; if {$p ne ""} { lappend pins $p } }
      if {![llength $pins]} { error "OT_DTSH_PAD $tap has no measurable sinks" }
      dict set sinkpins $tap $pins
    }
    set s 0.0; set mn Inf; set mx -Inf; set pins [dict get $sinkpins $tap]
    foreach p $pins { set v [expr {[get_property $p arrival_max_rise]*1.0}]; set s [expr {$s+$v}]; set mn [expr {min($mn,$v)}]; set mx [expr {max($mx,$v)}] }
    dict set res $tap [list [expr {$s/[llength $pins]}] $mn $mx [llength $pins]]
  }
  return $res
}
proc ::ot_dtsh_pad::unpad {blk tap} {
  variable chains
  if {![dict exists $chains $tap]} return
  set c [dict get $chains $tap]
  set inp [sigpin [$blk findInst $tap] INPUT]
  $inp disconnect
  foreach i [dict get $c cells] { odb::dbInst_destroy $i }
  foreach n [dict get $c nets] { odb::dbNet_destroy $n }
  $inp connect [dict get $c net]
  dict unset chains $tap
}
proc ::ot_dtsh_pad::pad {blk tap n master pg} {
  variable chains
  unpad $blk $tap
  if {$n <= 0} return
  set inst [$blk findInst $tap]; set inp [sigpin $inst INPUT]; set leaf [$inp getNet]
  lassign [$inst getLocation] tx ty
  set h [$master getHeight]
  set cells {}; set nets {}; set drv $leaf
  for {set k 0} {$k < $n} {incr k} {
    set c [odb::dbInst_create $blk $master "ot_dpad_${tap}_$k"]
    set o [odb::dbNet_create $blk "ot_dpad_${tap}_${k}_o"]; $o setSigType CLOCK
    foreach t [$c getITerms] {
      set mt [$t getMTerm]
      if {[$mt getSigType] in {POWER GROUND}} { $t connect [dict get $pg [$mt getSigType]]; continue }
      if {[$mt getIoType] eq "INPUT"} { $t connect $drv } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $o }
    }
    # stack beside the sub-tap (alternate rows above/below); detailed_placement legalises once after all chains
    set dy [expr {(($k/2)+1) * $h * (($k % 2) ? -1 : 1)}]
    $c setLocation $tx [expr {$ty + $dy}]; $c setPlacementStatus PLACED
    lappend cells $c; lappend nets $o; set drv $o
  }
  $inp disconnect; $inp connect $drv
  dict set chains $tap [dict create net $leaf cells $cells nets $nets]
}
proc ::ot_dtsh_pad::legalise {blk} {
  variable chains
  set before {}
  foreach i [$blk getInsts] {
    if {[string match ot_dpad_* [$i getName]] || [[$i getMaster] isBlock]} continue
    dict set before [$i getName] [$i getLocation]
  }
  dict for {tap c} $chains { foreach i [dict get $c cells] { $i setPlacementStatus PLACED } }
  detailed_placement
  set moved 0; set maxd 0
  dict for {name xy} $before {
    lassign [[$blk findInst $name] getLocation] x y
    set d [expr {abs($x-[lindex $xy 0])+abs($y-[lindex $xy 1])}]
    if {$d} { incr moved; set maxd [expr {max($maxd,$d)}] }
  }
  dict for {tap c} $chains { foreach i [dict get $c cells] { $i setPlacementStatus FIRM; $i setDoNotTouch 1 } }
  return [list $moved [expr {$maxd/double([$blk getDefUnits])}]]
}
proc ::ot_dtsh_pad::audit {blk} {
  variable chains
  dict for {tap c} $chains {
    set inp [sigpin [$blk findInst $tap] INPUT]; set net [$inp getNet]; set k [llength [dict get $c cells]]
    # walk up: each chain net has exactly one input load and is driven by the previous chain cell
    while {[string match ot_dpad_* [$net getName]]} {
      set loads 0; foreach it [$net getITerms] { if {[$it isInputSignal]} { incr loads } }
      if {$loads != 1} { error "OT_DTSH_PAD chain net [$net getName] fans out" }
      set drv ""; foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv [$it getInst] } }
      if {$drv eq "" || ![string match ot_dpad_${tap}_* [$drv getName]]} { error "OT_DTSH_PAD chain driver mismatch at [$net getName]" }
      set net [[sigpin $drv INPUT] getNet]; incr k -1
    }
    if {$k != 0 || $net ne [dict get $c net]} { error "OT_DTSH_PAD $tap chain does not end on its original leaf net" }
  }
  puts "OT_DTSH_PAD AUDIT PASS: [dict size $chains] padded sub-taps, every chain single-fanout and rooted on its original trunk leaf net"
}
proc ::ot_dtsh_pad::run {blk spec {opts {}}} {
  variable source_dir; variable chains
  set o [dict merge [dict create master BUFx2_ASAP7_75t_R iters 4 tol 6 default_stage 15 max_stages 16 dir /out] $opts]
  if {![dict exists $o pg]} { error "OT_DTSH_PAD needs explicit PG nets" }
  set master [[ord::get_db] findMaster [dict get $o master]]
  if {$master eq "NULL"} { error "OT_DTSH_PAD missing master [dict get $o master]" }
  set py [expr {[info exists ::env(OT_DTSH_PAD_PY)] ? $::env(OT_DTSH_PAD_PY) : [file join $source_dir shallow_clock_pad.py]}]
  set taps {}; set target {}; set kind {}
  foreach s $spec { lassign $s t k tt; lappend taps $t; dict set target $t $tt; dict set kind $t $k }
  set_propagated_clock [all_clocks]
  estimate_parasitics -placement
  set nat [measure $blk $taps]
  set n {}; foreach t $taps { dict set n $t 0 }
  set cur $nat; set summ ""
  for {set it 1} {$it <= [dict get $o iters]} {incr it} {
    set meas [file join [dict get $o dir] pad_meas_$it.tsv]; set plan [file join [dict get $o dir] pad_plan_$it.tsv]
    set fh [open $meas w]; puts $fh "tap\tkind\ttarget_ps\tnatural_ps\tmean_ps\tn_now"
    foreach t $taps { puts $fh "$t\t[dict get $kind $t]\t[dict get $target $t]\t[lindex [dict get $nat $t] 0]\t[lindex [dict get $cur $t] 0]\t[dict get $n $t]" }
    close $fh
    set summ [exec python3 $py $meas --out $plan --default-stage-ps [dict get $o default_stage] --tol-ps [dict get $o tol] --max-stages [dict get $o max_stages]]
    puts "OT_DTSH_PAD iter $it $summ"
    if {[json_int $summ changed] == 0 && $it > 1} break
    set fh [open $plan]; gets $fh
    set any 0
    while {[gets $fh line] >= 0} { lassign [split $line \t] t nn; if {$nn != [dict get $n $t]} { pad $blk $t $nn $master [dict get $o pg]; dict set n $t $nn; set any 1 } }
    close $fh
    if {!$any} break
    lassign [legalise $blk] moved maxd
    puts "OT_DTSH_PAD iter $it DPL existing_cells_moved $moved max_um $maxd"
    estimate_parasitics -placement
    set cur [measure $blk $taps]
  }
  audit $blk
  set res {}
  foreach t $taps { dict set res $t [dict create n [dict get $n $t] natural [lindex [dict get $nat $t] 0] mean [lindex [dict get $cur $t] 0] min [lindex [dict get $cur $t] 1] max [lindex [dict get $cur $t] 2] sinks [lindex [dict get $cur $t] 3] target [dict get $target $t] kind [dict get $kind $t]] }
  return $res
}
# minimal flat-JSON integer field reader for the sizer's one-line summary
proc ::ot_dtsh_pad::json_int {s key} {
  if {![regexp "\"$key\": (-?\[0-9\]+)" $s -> v]} { error "OT_DTSH_PAD sizer summary lacks $key" }
  return $v
}
