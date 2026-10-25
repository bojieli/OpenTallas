# QC-PHYS f57: mean clock arrival of the boundary (pin) registers -- the signoff.py F1 rule set (registers with a data
# pin fed from an input port or driving an output port).  prop = arrival_min_rise (FF / hold view) | arrival_max_rise.
proc ot_pinreg_mean {prop} {
  set din [all_inputs -no_clocks]; set regs {}; set bnd {}; set async {}; set data {}
  foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
  foreach p [all_registers -async_pins] { dict set async [get_full_name $p] 1 }
  foreach p [all_registers -data_pins] { set n [get_full_name $p]; if {![dict exists $async $n]} { dict set data $n 1 } }
  foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]; if {![dict exists $data $n]} continue
    set i [regsub {/[^/]+$} $n {}]; if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]; if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
  set n 0; set s 0.0
  dict for {i x} $bnd { set a [get_property [dict get $regs $i] $prop]; if {[string is double -strict $a]} { incr n; set s [expr {$s + $a}] } }
  if {!$n} { error "ot_pinreg_mean: no boundary registers" }
  return [format %.1f [expr {$s / $n}]]
}
# vclk := boundary-register mean (env value "auto") or the env number; tag for the log
proc ot_vclk_bind {envv prop tag} {
  if {![info exists ::env($envv)] || $::env($envv) eq ""} return
  set v $::env($envv); if {$v eq "auto"} { set v [ot_pinreg_mean $prop] }
  set_clock_latency -source $v [get_clocks vclk]; puts "$tag vclk source latency := $v ($envv=$::env($envv), $prop)"
}
