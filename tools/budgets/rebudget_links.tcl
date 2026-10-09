# REBUDGET 2026-10-08 (tools/budgets/rebudget.py): die-level LINK DUMP, sourced at the end of a die STA session
# (S81 die_sta.py kit + r3 GRT SPEF; HBM hbm_die_relay_sta.py in-session GRT) after the clocks, latencies and
# uncertainties are set.  For every (scoped instance, data bus, direction) it records the worst die timing path
# through that bus at the session's corner (max = setup at TT, min = hold at FF):
#   P  mm inst bus dir start_pin end_pin start_clk end_clk T lat_s lat_r arr_out arr_in req margin slack   (ps)
#      lat_s / lat_r = launch / capture clock latency at the pins (the die plan), arr_out = arrival at the path's first
#      point (the sender's output pin: ETM / interim lib startpoint), arr_in = data arrival at the receiver pin,
#      req = data required time, margin = the receiver lib check (setup / hold).  Wire + relays = arr_in - arr_out.
#   E  mm inst bus dir drv_pin load_pin wire_ps         a bus with no constrained path (a side with no timing view):
#      the die wire alone, from the timing-graph wire edges (GRT parasitics)
#   L  pin latency_ps clock                              the HBM session's planned clock-pin latencies ($ot_lat)
#   (P lines carry 3 more fields: cap_time = the capture edge time (target_clk_time, ps), cap_tr = rise / fall,
#    fo_arc fo_pin = for a FORWARDED-clock capture (end clock ot_fw_*): the forwarded-clock pin's clock-pin -> it arc
#    (ps) and the pin; else "-")
# Scope file: one instance name per line.  Cost: one find_timing_paths per (instance, bus, direction).
#
# FORWARDED-CLOCK (source-synchronous) links: S81 l2r / svc / selector outputs send data WITH a forwarded clock
# (fo = cks) through a chain of station views that capture on the forwarded clock (dsfd_stn*: di0 setup_falling vs
# fi0).  The die kit defines no clock on a forwarded-clock pin, so those links are untimed (E lines).  ot_rb_fwd_clocks
# (call before ot_rb_dump) makes them timed: for every net touching a scoped instance whose load is a clock pin
# (is_clock) and whose driver is an instance output, a clock ot_fw_<n> on the driver pin
# (a clock created ON the driver pin -- create_generated_clock does not carry an ideal master's pin latency --
# with source latency = the planned latency of the driver's clock pin + the lib arc into the forwarded pin; a root
# clock ot_fwr_<n> at an upstream station's clock pin with none), propagated, with the session's uncertainty.  The common launch latency cancels, so the hop is
# judged on (data arc - forwarded-clock arc) + (data wire - clock wire) + the station check, the source-synchronous
# frame.
proc ot_rb_fwd_clocks {scope_file period unc_s unc_h mm {lat_file ""}} {
  # period / unc_s / unc_h in ps; mm = max (setup session) | min (hold session); lat_file = the kit's planned
  # clock-pin latencies (set_clock_latency <v> [get_pins -quiet {<pin> ...}]), else $::ot_lat {clock latency pin}
  set u [sta::time_sta_ui 1e-12]
  set lat [dict create]
  if {$lat_file ne "" && [file exists $lat_file]} {
    set fh [open $lat_file]
    while {[gets $fh ln] >= 0} {
      if {[regexp {^set_clock_latency\s+([-0-9.eE]+)\s+\[get_pins -quiet \{(\S+)} $ln -> v pn]} { if {![dict exists $lat $pn]} { dict set lat $pn $v } }
    }
    close $fh
  } elseif {[info exists ::ot_lat]} { foreach e $::ot_lat { lassign $e d l pins; foreach p $pins { dict set lat [get_full_name $p] $l } } }
  set fh [open $scope_file]; set insts [split [string trim [read $fh]] "\n"]; close $fh
  set done [dict create]; set n 0; set nr 0
  set srcs {}
  foreach c [all_clocks] { foreach s [get_property $c sources] { lappend srcs [get_full_name $s] } }
  foreach iname $insts {
    set inst [get_cells -quiet $iname]
    if {![llength $inst]} continue
    foreach p [get_pins -quiet -of_objects $inst] {
      set net [get_nets -quiet -of_objects $p]
      if {![llength $net]} continue
      set ck 0
      foreach l [get_pins -quiet -of_objects $net -filter "direction==input"] { if {[get_property $l is_clock]} { set ck 1; break } }
      if {!$ck} continue
      foreach d [get_pins -quiet -of_objects $net -filter "direction==output"] {
        set dn [get_full_name $d]
        if {[dict exists $done $dn] || [lsearch -exact $srcs $dn] >= 0} continue
        dict set done $dn 1
        # the driver's clock pin with an arc into the forwarded-clock pin, and that arc (this session's corner)
        set di [get_cells -of_objects $d]; set x ""; set arc -1
        foreach q [get_pins -quiet -of_objects $di -filter "direction==input"] {
          if {![get_property $q is_clock]} continue
          if {[catch {get_timing_edges -from $q -to $d} es] || ![llength $es]} continue
          set x $q
          foreach e $es {
            set v [expr {$mm eq "max" ? max([get_property $e delay_max_rise], [get_property $e delay_max_fall])
                                      : min([get_property $e delay_min_rise], [get_property $e delay_min_fall])}]
            if {$v > $arc} { set arc $v }
          }
          break
        }
        if {$x eq "" || $arc < 0} continue
        set xn [get_full_name $x]; regsub {\[0\]$} $xn {} xb
        # the planned (ideal) latency at the driver's clock pin; none = an upstream forwarded clock (root, 0)
        set L ""
        foreach k [list $xn $xb] { if {$L eq "" && [dict exists $lat $k]} { set L [dict get $lat $k] } }
        set root [expr {$L eq ""}]
        if {$root} {
          set L 0
          if {[lsearch -exact $srcs $xn] < 0} {
            set rn ot_fwr_$nr; incr nr
            create_clock -name $rn -period [expr {$period * $u}] $x
            set_propagated_clock [get_clocks $rn]
            set_clock_uncertainty -setup [expr {$unc_s * $u}] [get_clocks $rn]
            set_clock_uncertainty -hold [expr {$unc_h * $u}] [get_clocks $rn]
            lappend srcs $xn
          }
        }
        # a root clock ON the forwarded-clock pin at (planned latency of the driver's clock pin + its arc), propagated
        # from there through the die wire / stations: the hop is then timed in the source-synchronous frame
        set gn ot_fw_$n; incr n
        if {[catch {create_clock -name $gn -period [expr {$period * $u}] $d} e]} { puts "OT_FWD_ERR $dn $e"; continue }
        set_propagated_clock [get_clocks $gn]
        set_clock_latency -source [expr {$L + $arc}] [get_clocks $gn]
        set_clock_uncertainty -setup [expr {$unc_s * $u}] [get_clocks $gn]
        set_clock_uncertainty -hold [expr {$unc_h * $u}] [get_clocks $gn]
        set ::ot_rb_fwarc($gn) [list [format %.1f [expr {$arc / $u}]] $dn]
        puts "OT_FWD $gn $dn src $xn L [format %.1f [expr {$L / $u}]] arc [format %.1f [expr {$arc / $u}]] root $root"
        lappend srcs $dn
      }
    }
  }
  puts "OT_FWD_CLOCKS $n roots $nr"
}
proc ot_rb_capinfo {pe u} {
  set t "-"; set tr "-"
  catch {set t [format %.1f [expr {[$pe target_clk_time] * 1e12}]]}
  catch {set tr [$pe target_clk_end_trans]}
  return [join [list $t $tr] "\t"]
}
proc ot_rb_fo_arc {ec u mm} {
  # forwarded-clock capture (end clock ot_fw_*): the driver's clock-pin -> forwarded-clock-pin arc (ps) and the pin
  set n [get_full_name $ec]
  if {![info exists ::ot_rb_fwarc($n)]} { return "-\t-" }
  return [join $::ot_rb_fwarc($n) "\t"]
}
proc ot_rb_dump {mm out scope_file} {
  set u [sta::time_sta_ui 1e-12]
  catch {suppress_msg 101 363}
  set f [open $out w]
  set fh [open $scope_file]; set insts [split [string trim [read $fh]] "\n"]; close $fh
  puts $f "# ot_rb_dump $mm [llength $insts] instances, UI per ps $u"
  # A planned clock entry can contain several literal pins (e.g. eight HC bank clocks).
  # OpenSTA get_full_name accepts one object, so expand the collection without changing its latency.
  if {[info exists ::ot_lat]} { foreach e $::ot_lat { lassign $e d l pins; foreach p $pins { puts $f "L\t[get_full_name $p]\t[format %.1f [expr {$l / $u}]]\t$d" } } }
  set np 0; set ne 0
  foreach iname $insts {
    set inst [get_cells -quiet $iname]
    if {![llength $inst]} { puts $f "X\t$iname\tnoinst"; continue }
    set g [dict create]
    foreach p [get_pins -quiet -of_objects $inst] {
      set d [get_property $p direction]
      if {$d ne "input" && $d ne "output"} continue
      if {[get_property $p is_clock]} continue
      set n [get_property $p lib_pin_name]
      regsub {\[[0-9]+\]$} $n {} b
      dict lappend g "$b $d" $p
    }
    dict for {k pins} $g {
      lassign $k b d
      set best ""; set bs 1e30
      if {$d eq "input"} { set pes [find_timing_paths -path_delay $mm -to $pins -group_path_count 1 -endpoint_path_count 1]
      } else { set pes [find_timing_paths -path_delay $mm -through $pins -group_path_count 1 -endpoint_path_count 1] }
      foreach pe $pes {
        if {[$pe is_unconstrained] || ![$pe is_check]} continue
        set s [$pe slack]
        if {$s < $bs} { set bs $s; set best $pe }
      }
      if {$best ne ""} {
        set pts [get_property $best points]
        set p0 [lindex $pts 0]
        set ec [get_property $best endpoint_clock]
        set sc [get_property $best startpoint_clock]
        puts $f [join [list P $mm $iname $b $d [get_full_name [get_property $p0 pin]] [get_full_name [get_property $best endpoint]] \
          [get_full_name $sc] [get_full_name $ec] [format %.3f [expr {[get_property $ec period] / $u}]] \
          [format %.1f [expr {[$best source_clk_latency] * 1e12}]] [format %.1f [expr {[$best target_clk_delay] * 1e12}]] \
          [format %.1f [expr {[get_property $p0 arrival] / $u}]] [format %.1f [expr {[$best data_arrival_time] * 1e12}]] \
          [format %.1f [expr {[$best data_required_time] * 1e12}]] [format %.1f [expr {[$best margin] * 1e12}]] \
          [format %.1f [expr {$bs * 1e12}]] [ot_rb_capinfo $best $u] [ot_rb_fo_arc $ec $u $mm]] "\t"]
        incr np
        continue
      }
      # no constrained path through this bus: the wire alone (worst over the first 8 bits)
      set w -1; set wd ""; set wl ""
      foreach p [lrange $pins 0 7] {
        set net [get_nets -quiet -of_objects $p]
        if {![llength $net]} continue
        if {$d eq "input"} { set drv [get_pins -quiet -of_objects $net -filter "direction==output"]; set lds [list $p]
        } else { set drv [list $p]; set lds [get_pins -quiet -of_objects $net -filter "direction==input"] }
        foreach dv $drv { foreach ld $lds {
          if {[catch {get_timing_edges -from $dv -to $ld} es]} { set es {} }
          foreach e $es {
            set v [expr {$mm eq "max" ? max([get_property $e delay_max_rise], [get_property $e delay_max_fall])
                                      : min([get_property $e delay_min_rise], [get_property $e delay_min_fall])}]
            if {$v / $u > $w} { set w [expr {$v / $u}]; set wd [get_full_name $dv]; set wl [get_full_name $ld] }
          } } }
      }
      if {$w >= 0} { puts $f [join [list E $mm $iname $b $d $wd $wl [format %.1f $w]] "\t"]; incr ne }
    }
  }
  close $f
  catch {unsuppress_msg 101 363}
  puts "OT_RB_DUMP $mm paths $np wires $ne -> $out"
}
