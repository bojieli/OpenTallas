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
# Scope file: one instance name per line.  Cost: one find_timing_paths per (instance, bus, direction).
proc ot_rb_dump {mm out scope_file} {
  set u [sta::time_sta_ui 1e-12]
  catch {suppress_msg 101 363}
  set f [open $out w]
  set fh [open $scope_file]; set insts [split [string trim [read $fh]] "\n"]; close $fh
  puts $f "# ot_rb_dump $mm [llength $insts] instances, UI per ps $u"
  if {[info exists ::ot_lat]} { foreach e $::ot_lat { lassign $e d l p; puts $f "L\t[get_full_name $p]\t[format %.1f [expr {$l / $u}]]\t$d" } }
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
          [format %.1f [expr {$bs * 1e12}]]] "\t"]
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
