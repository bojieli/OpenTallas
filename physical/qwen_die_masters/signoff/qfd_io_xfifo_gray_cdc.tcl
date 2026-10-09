# Approved I12: only published Gray pointer -> first synchronizer crossings.
# No clock-group cut, payload-memory exception, online/reset exception, or RTL change.
# This OpenSTA build has no -datapath_only option.  Its supported
# -ignore_clock_latency keeps a conservative max-delay check (including
# library setup/clk->q terms; -through Q and -to D scope the Gray bus); only the asynchronous Gray hold check is cut.
proc ot_xfifo_gray_cdc_constraints {budget} {
  set cells [all_registers -cells]
  set checked 0
  foreach prefix {u_ut u_ur u_st u_sr u_sq} {
    foreach {source target} {wr_gray_pub wr_gray_r1 rd_gray rd_gray_w1} {
      set from {};set to {}
      foreach cell $cells {
        set name [get_full_name $cell]
        set stem "${prefix}.g_afw.u_af."
        if {[string first $stem $name] != 0} continue
        set suffix [string range $name [string length $stem] end]
        if {[regexp [format {^%s\[[0-9]+\]} $source] $suffix]} {lappend from $cell}
        if {[regexp [format {^%s\[[0-9]+\]} $target] $suffix]} {lappend to $cell}
      }
      # Gray MSB is identical to binary MSB; synthesis aliases rd_gray[MSB]
      # to rd_bin[MSB]. Include only the actually missing bit, never the
      # whole binary pointer/read-mux cone.
      if {$source eq "rd_gray" && [llength $from] < [llength $to]} {
        set high -1
        foreach cell $to {
          regexp {rd_gray_w1\[([0-9]+)\]} [get_full_name $cell] -> bit
          if {$bit > $high} {set high $bit}
        }
        foreach cell $cells {
          set name [get_full_name $cell]
          set stem "${prefix}.g_afw.u_af."
          if {[string first $stem $name] != 0} continue
          set suffix [string range $name [string length $stem] end]
          if {[regexp [format {^rd_bin\[%d\]} $high] $suffix]} {lappend from $cell}
        }
      }
      if {[llength $from] == 0 || [llength $from] != [llength $to]} {
        error "OT_XFIFO_GRAY unbound $prefix $source->$target [llength $from]/[llength $to]"
      }
      set qpins {};set dpins {}
      foreach pin [get_pins -of_objects $from] {
        if {[regexp {/Q(N)?$} [get_full_name $pin]]} {lappend qpins $pin}
      }
      foreach pin [get_pins -of_objects $to] {
        if {[regexp {/D$} [get_full_name $pin]]} {lappend dpins $pin}
      }
      if {[llength $qpins] == 0 || [llength $dpins] == 0} {error "OT_XFIFO_GRAY missing Q/D pins"}
      set_max_delay -ignore_clock_latency $budget -from $from -through $qpins -to $dpins
      set_false_path -hold -from $from -through $qpins -to $dpins
      incr checked [llength $to]
      puts "OT_XFIFO_GRAY $prefix $source->$target width=[llength $to] max=$budget hold=async"
    }
  }
  puts "OT_XFIFO_GRAY_TOTAL $checked first-stage synchronizer bits"
}
set ot_xfifo_gray_budget [expr {[get_property [get_clocks ck] period] - 60.0}]
ot_xfifo_gray_cdc_constraints $ot_xfifo_gray_budget
unset ot_xfifo_gray_budget
