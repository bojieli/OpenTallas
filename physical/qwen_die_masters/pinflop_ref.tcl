# PINFLOP-REF (drive-0849 2026-10-10, coordinator class-1 fix: 39 hold floods at CTS/GRT): the IO reference register used
# to be the FIRST register of the design / clock (an arbitrary tree position), so the input min delay sat far from the
# capture flops' clock and CTS / GRT hold repair flooded (ehash / core18 / kvwq closed only after naming the input pin
# flops by hand).  When the block has a REGISTERED input boundary -- input ports reaching register D pins directly or
# through <= 2 buffers ("pin flops") -- the reference is the pin flop of MEDIAN clock arrival.  No pin flops -> the
# previous reference.  An explicit matching OT_REF_GLOB keeps priority; OT_REF_PINFLOP=0 opts out.
# PF-HOLDPAD (NATIVE-REF 2026-10-18, S81-SMHKP4 finding): (a) after CTS / GRT hold repair a pin flop sits behind the
# input hold pad + driver + CTS hold buffers (smhq d[24]: HB2 ot_inhold -> BUFx4f ot_ihdrv -> HB2 -> BUFx2 -> ... -> D):
# the 3-hop search lost every pin flop at GRT, the reference fell to the FIRST register (a hard child's raw clock pin
# g_l[0].u_sml/ck, ~250 ps before the pin flops) and GRT hold repair padded all 341 inputs (3,756 buffers).  Past the
# first 3 hops the search now follows single-load BUF / HB chains (hold pads are inserted in series) up to OT_PF_HOPS
# (default 32) hops; fan-out trees past hop 3 are not followed, so a deep reset tree never makes every flop a pin flop.
# (b) a hard child (a macro whose Liberty clock pin carries min/max_clock_tree_path: an ETM view) reached by an input is a
# pin "flop" at its clock pin + its internal insertion (kp4_dec, a wires-only parent: the reference was the raw child
# clock pin u_chn/clk, ~250 ps before the child's flops -> 10k hold buffers).  ot_pf_arr PIN max|min is the arrival every
# caller reads: pin arrival + that internal insertion for a hard-child clock pin (also when OT_REF_GLOB or the
# first-register fallback names one), the plain pin arrival otherwise.  Insertion is read from the bound ETM Liberty
# files (ADDITIONAL_LIBS; an FF-only session uses the _ff sibling of a _tt lib).
proc ot_pf_lib_ins {} {
  # {lib cell -> {clock pin -> {max min}}} from the hard-child Liberty files of this session (cached)
  # FF values: an FF-only session, or the BC scene of a multi-scene session (::ot_ioref_scene, io_ref_routed.sdc)
  set ff [expr {([info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC") ||
                (![catch {llength [get_libs -quiet *FF*]} nf] && $nf && ![catch {llength [get_libs -quiet *TT*]} nt] && !$nt)}]
  if {[info exists ::ot_pf_libins_c] && [dict exists $::ot_pf_libins_c $ff]} { return [dict get $::ot_pf_libins_c $ff] }
  if {![info exists ::ot_pf_libins_c]} { set ::ot_pf_libins_c [dict create] }
  set ::ot_pf_libins [dict create]
  set libs {}
  foreach v {ADDITIONAL_LIBS OT_PF_MACRO_LIBS} { if {[info exists ::env($v)]} { lappend libs {*}$::env($v) } }
  foreach lib $libs {
    if {$ff} { regsub {_tt(\.lib(\.gz)?)$} $lib {_ff\1} l2; if {[file readable $l2]} { set lib $l2 } }
    if {![file readable $lib] || [string match *.gz $lib]} continue
    if {[catch {set f [open $lib]; set txt [read $f]; close $f}]} continue
    if {![regexp {cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)} $txt -> cell]} continue
    foreach chunk [lrange [regexp -all -inline -indices {pin\s*\(\s*"?[^")]+"?\s*\)\s*\{} $txt] 0 end] {
      set s [lindex $chunk 0]
      set body [string range $txt $s [expr {$s + 2000}]]
      if {![regexp {^pin\s*\(\s*"?([^")]+)"?\s*\)} $body -> pn]} continue
      set nxt [string first "pin(" $body 4]; if {$nxt > 0} { set body [string range $body 0 $nxt] }
      set mx ""; set mn ""
      regexp {max_clock_tree_path;\s*cell_rise\s*\(\s*scalar\s*\)\s*\{\s*values\s*\(\s*"([-0-9.eE]+)"} $body -> mx
      regexp {min_clock_tree_path;\s*cell_rise\s*\(\s*scalar\s*\)\s*\{\s*values\s*\(\s*"([-0-9.eE]+)"} $body -> mn
      if {$mx eq "" && $mn eq ""} continue
      if {$mx eq ""} { set mx $mn }
      if {$mn eq ""} { set mn $mx }
      dict set ::ot_pf_libins $cell $pn [list $mx $mn]
    }
  }
  dict set ::ot_pf_libins_c $ff $::ot_pf_libins
  return $::ot_pf_libins
}
proc ot_pf_ins {pin mm} {
  # internal insertion behind PIN when it is a hard child's clock pin (else 0)
  set c [get_cells -quiet -of_objects $pin]
  if {![llength $c]} { return 0.0 }
  set li [ot_pf_lib_ins]
  set ref [get_property $c ref_name]
  if {![dict exists $li $ref]} { return 0.0 }
  set pn [get_property $pin lib_pin_name]
  if {![dict exists $li $ref $pn]} { return 0.0 }
  return [lindex [dict get $li $ref $pn] [expr {$mm eq "min" ? 1 : 0}]]
}
proc ot_pf_arr {pin mm} {
  set a [get_property $pin [expr {$mm eq "min" ? "arrival_min_rise" : "arrival_max_rise"}]]
  if {![string is double -strict $a]} { return $a }
  return [expr {$a + [ot_pf_ins $pin $mm]}]
}
proc ot_pf_clks {ports} {
  set seen [dict create]; set out {}; set vis [dict create]
  set li [ot_pf_lib_ins]
  set lim [expr {[info exists ::env(OT_PF_HOPS)] && [string is integer -strict $::env(OT_PF_HOPS)] ? $::env(OT_PF_HOPS) : 32}]
  foreach port $ports {
    set nets [get_nets -quiet [get_full_name $port]]
    for {set hop 0} {$hop < $lim && [llength $nets]} {incr hop} {
      set next {}
      foreach n $nets {
        set lds {}
        foreach pin [get_pins -quiet -of_objects $n] {
          if {[string first / [get_full_name $pin]] < 0} { continue }
          if {[get_property $pin direction] ne "input"} { continue }
          lappend lds $pin
        }
        # past the first 3 hops only single-load chains (series hold pads) are followed
        set follow [expr {$hop < 3 || [llength $lds] == 1}]
        foreach pin $lds {
          set c [get_cells -quiet -of_objects $pin]
          if {![llength $c]} { continue }
          set fn [get_full_name $c]
          set ck [get_pins -quiet "$fn/CLK"]
          set ref [get_property $c ref_name]
          if {[llength $ck]} {
            if {[get_property $pin lib_pin_name] ne "CLK" && ![dict exists $seen $fn]} { dict set seen $fn 1; lappend out $ck }
          } elseif {[dict exists $li $ref]} {
            # a hard child: its clock pin(s), counted at pin arrival + internal insertion (ot_pf_arr)
            if {![dict exists $li $ref [get_property $pin lib_pin_name]] && ![dict exists $seen $fn]} {
              dict set seen $fn 1
              foreach cp [dict keys [dict get $li $ref]] {
                set p [get_pins -quiet "$fn/$cp"]
                if {[llength $p]} { lappend out $p }
              }
            }
          } elseif {$follow && ![dict exists $vis $fn] && [regexp {^(BUF|HB)} $ref]} {
            dict set vis $fn 1
            foreach op [get_pins -quiet -of_objects $c] {
              if {[get_property $op direction] eq "output"} { lappend next [get_nets -quiet -of_objects $op] }
            }
          }
        }
      }
      set nets $next
    }
  }
  return $out
}
proc ot_pf_ref {ports} {
  if {[info exists ::env(OT_REF_PINFLOP)] && $::env(OT_REF_PINFLOP) eq "0"} { return {} }
  catch {sta::worst_slack_cmd max}   ;# arrivals need an updated timing graph (as the QDM reference reads below)
  set pf {}; set nh 0
  foreach p [ot_pf_clks $ports] {
    set a [ot_pf_arr $p max]
    if {[string is double -strict $a]} { lappend pf [list $a $p]; if {[ot_pf_ins $p max] != 0.0} { incr nh } }
  }
  if {![llength $pf]} { return {} }
  set pf [lsort -real -index 0 $pf]
  set m [lindex $pf [expr {[llength $pf] / 2}]]
  puts "QDM PINFLOP reference: [llength $pf] input pin flops ($nh hard-child clock pins at +insertion), median arrival [lindex $m 0] (range [lindex [lindex $pf 0] 0] .. [lindex [lindex $pf end] 0])"
  return [lindex $m 1]
}
# GLOB-MEDIAN (drive-0849 2026-10-10): a matching REFGLOB names a register GROUP (usually the input pin flops); the
# reference is its member of median clock arrival, not the first match (an arbitrary tree position).
proc ot_pf_median {pins label} {
  catch {sta::worst_slack_cmd max}
  set pf {}
  foreach p $pins {
    set a [ot_pf_arr $p max]
    if {[string is double -strict $a]} { lappend pf [list $a $p] }
  }
  if {![llength $pf]} { return {} }
  set pf [lsort -real -index 0 $pf]
  set m [lindex $pf [expr {[llength $pf] / 2}]]
  puts "QDM $label reference: [llength $pf] registers, median arrival [lindex $m 0] (range [lindex [lindex $pf 0] 0] .. [lindex [lindex $pf end] 0])"
  return [lindex $m 1]
}
