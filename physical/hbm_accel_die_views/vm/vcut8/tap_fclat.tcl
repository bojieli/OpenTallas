# tap_fclat.tcl (hbm-phys vm8 2026-10-10): per-tap source latency of a VM8 vertical-cut half from THIS session's own clock tree.
#
# Why: the die balances every tap leaf ck<f><i> of a half so that the half's pin registers arrive at one instant REF.  The
# block STA models that with  set_clock_latency -source (REF - f_tap)  per tap port.  tap_latency.py measured f_tap on the
# job's CALIBRATE CTS db, but the route builds its own tree: FF boundary arrivals in route 184.7..293.9 ps (nwe-6ae lvt,
# 4_1_cts, io_ref_routed census) and 296.7..471.0 (sew-2a2 lvt) against 294.5..367.6 on its calibrate db, so the
# per-tap offsets no longer cancel and both pin classes fail hold at CTS (port->face late capture, face->port early
# launch; 13-19k endpoints, -52..-137 ps, buffer-cap stalls).  The die tree is built after the blocks and balances the
# blocks' real leaf insertions (hierarchical CTS against the block's published clock-pin insertion), so the per-tap
# source latency must come from the tree the half is routed and signed off with.  Same rule as FLOW-IOREF (the routed
# tree is the truth, not the calibrate run).
#
# ot_fcl_apply <tag>: with propagated clocks and a built tree, for every tap port: source latency 0, mean propagated
# arrival f_tap of the posedge registers the tap drives (negedge lockups skipped; walked through the tap's buffers in
# the db), REF = max f_tap, set_clock_latency -source (REF - f_tap).  Arrivals are this session's corner: a single-scene
# session (corner_sta, hold ECO) reads get_property; a multi-scene (OT_HOLD_MM) session reads report_arrival of
# ::ot_ioref_scene (BC in ot_mm_sync's FF read) or of the setup scene (CTS hook, mode ss).  With ideal clocks or no
# tree it does nothing (the calibrated values written above it by tap_latency.py stay).  Prints one OT_FCL line per
# call and writes the per-tap die requirement to $RESULTS_DIR (flow) or /work (corner_sta) as fclat_<tag>_<scene>.txt
# (tap, mean, source latency, sinks, min, max).
proc ot_fcl_taps {} {
  set r {}
  foreach bt [[ord::get_db_block] getBTerms] {
    set n [regsub {\[0\]$} [$bt getName] {}]
    if {[regexp {^ck[wens][0-9]+$} $n] && [$bt getNet] ne "NULL"} { lappend r [list $n [$bt getNet]] }
  }
  return $r
}
# posedge register clock pins of one tap (STA pin objects) and whether the tap net carries a built tree
proc ot_fcl_sinks {net} {
  set todo [list $net]; set seen [dict create]; set pins {}; set tree 0
  while {[llength $todo]} {
    set nt [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {$nt eq "NULL" || [dict exists $seen [$nt getName]]} { continue }
    dict set seen [$nt getName] 1
    foreach it [$nt getITerms] {
      if {[$it isOutputSignal]} { continue }
      set inst [$it getInst]; set m [$inst getMaster]
      if {[$m isSequential]} {
        set nm [$inst getName]
        if {[string match *DFFL* [$m getName]] || [string match *_DFF_N* $nm]} { continue }
        set mt [[$it getMTerm] getName]
        set p [get_pins -quiet "[string map {[ \\[ ] \\]} [string map {\\ {}} $nm]]/$mt"]
        if {![llength $p]} { set p [get_pins -quiet "$nm/$mt"] }
        if {[llength $p]} { lappend pins $p }
      } else {
        set tree 1
        foreach o [$inst getITerms] { if {[$o isOutputSignal]} { lappend todo [$o getNet] } }
      }
    }
  }
  return [list $pins $tree]
}
proc ot_fcl_scene {} {
  if {[catch {sta::multi_scene} ms] || !$ms} { return "" }
  if {[info exists ::ot_ioref_scene]} { return $::ot_ioref_scene }
  if {[llength [info procs ot_mm_sc]]} { return [ot_mm_sc] }
  return WC
}
# propagated arrival of the rising clock at a register clock pin, produced by the source rise edge, in this scene
proc ot_fcl_arr {p sc} {
  if {$sc eq ""} {
    set v [get_property $p arrival_max_rise]
    return [expr {[string is double -strict $v] ? $v : ""}]
  }
  sta::redirect_string_begin
  catch {report_arrival -scene $sc -digits 4 $p}
  set r [sta::redirect_string_end]
  set v ""
  foreach {- ck e rv fv} [regexp -all -inline {\((\S+) ([\^v])\)\s+r\s+(\S+)\s+f\s+(\S+)} $r] {
    if {$e ne "^"} continue
    set x [lindex [split $rv :] end]
    if {[string is double -strict $x] && ($v eq "" || $x > $v)} { set v $x }
  }
  return $v
}
proc ot_fcl_apply {tag} {
  set ck [get_clocks -quiet core_clk]
  if {![llength $ck] || [catch {get_property $ck is_propagated} prop] || !$prop} {
    puts "OT_FCL $tag: clocks ideal -> calibrated tap latencies kept"; return
  }
  set taps [ot_fcl_taps]
  set sc [ot_fcl_scene]
  set built 0; set meas {}
  foreach t $taps { lassign $t n net; lassign [ot_fcl_sinks $net] pins tree; set built [expr {$built || $tree}]; lappend meas [list $n $pins] }
  if {!$built} { puts "OT_FCL $tag: no clock tree on the taps -> calibrated tap latencies kept"; return }
  foreach t $taps { set_clock_latency -source 0 [get_ports -quiet "[lindex $t 0]\[0\]"] }
  set f [dict create]; set st [dict create]; set nsink 0; set spread 0.0
  foreach m $meas {
    lassign $m n pins
    set s 0.0; set k 0; set lo 1e9; set hi -1e9
    foreach p $pins {
      set v [ot_fcl_arr $p $sc]
      if {$v eq ""} continue
      set s [expr {$s + $v}]; incr k
      if {$v < $lo} { set lo $v }; if {$v > $hi} { set hi $v }
    }
    if {$k} { dict set f $n [expr {$s / $k}]; dict set st $n [list $k $lo $hi]; incr nsink $k; if {$hi - $lo > $spread} { set spread [expr {$hi - $lo}] } }
  }
  if {![dict size $f]} { puts "OT_FCL $tag: no measurable tap sinks -> calibrated tap latencies kept"; return }
  set ref -1e9; set lo 1e9
  dict for {n v} $f { if {$v > $ref} { set ref $v }; if {$v < $lo} { set lo $v } }
  set od [expr {[info exists ::env(RESULTS_DIR)] && [file isdirectory $::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : ([file isdirectory /work] && [file writable /work] ? "/work" : "")}]
  set fh ""
  if {$od ne ""} { catch {set fh [open $od/fclat_${tag}_[expr {$sc eq "" ? "single" : $sc}].txt w]} }
  dict for {n v} $f {
    set_clock_latency -source [format %.1f [expr {$ref - $v}]] [get_ports -quiet "$n\[0\]"]
    if {$fh ne ""} { lassign [dict get $st $n] k tlo thi; puts $fh [format "%s %.1f %.1f %d %.1f %.1f" $n $v [expr {$ref - $v}] $k $tlo $thi] }
  }
  if {$fh ne ""} { close $fh }
  puts [format "OT_FCL %s scene %s: %d taps %d sinks, tap mean %.1f .. %.1f ps -> REF %.1f (source latency 0 .. %.1f); worst in-tap spread %.1f ps" \
    $tag [expr {$sc eq "" ? "single" : $sc}] [dict size $f] $nsink $lo $ref $ref [expr {$ref - $lo}] $spread]
}
