# Exact native ot_fdi_phy_cdc contract. No whole-domain clock groups.
proc ot_fdi_phy_cdc_constraints {core phy tcore tphy margin} {
  set fast [expr {0.5 * min($tcore, $tphy)}]
  foreach k {rx_ptr tx_ptr rx_mem tx_mem level reset} {set L($k) {}}
  foreach cell [all_registers -cells] {
    set n [get_full_name $cell]
    if {![regexp {[.]u_fdi_cdc[.]} $n]} {continue}
    if {[regexp {[.]u_(rx|tx)[.](wr_gray_r1|rd_gray_w1|wr_online_r1|rd_online_w1)(\[[0-9]+\])?(\$[^ ]*)?$} $n -> side]} {
      lappend L(${side}_ptr) $cell
    } elseif {[regexp {[.]u_(rx|tx)[.]mem\[} $n -> side]} {
      lappend L(${side}_mem) $cell
    } elseif {[regexp {[.]up_s\[0\](\$[^ ]*)?$} $n]} {
      lappend L(level) $cell
    } elseif {[regexp {[.](u_crs|u_prs|wr_reset_conditioner|rd_reset_conditioner)[.]reset_pipe\[0\](\$[^ ]*)?$} $n]} {
      lappend L(reset) $cell
    }
  }
  foreach k {rx_ptr tx_ptr rx_mem tx_mem level reset} {
    if {![llength $L($k)]} {error "FDI_PHY_CDC missing exact native register class $k"}
  }
  foreach k {rx_ptr tx_ptr} {
    set_max_delay -ignore_clock_latency $fast -to $L($k)
    set_false_path -hold -to $L($k)
  }
  foreach {kind dest period} [list rx_mem $core $tcore tx_mem $phy $tphy] {
    set_max_delay -ignore_clock_latency [expr {$period - $margin}] -from $L($kind) -to [get_clocks $dest]
    set_false_path -hold -from $L($kind) -to [get_clocks $dest]
  }
  # Single-bit status and reset synchronizer first stages only; second stages stay timed.
  foreach k {level reset} {set_false_path -to $L($k)}
  puts "FDI_PHY_CDC exact constraints: rxptr=[llength $L(rx_ptr)] txptr=[llength $L(tx_ptr)] rxmem=[llength $L(rx_mem)] txmem=[llength $L(tx_mem)] level=[llength $L(level)] reset=[llength $L(reset)]"
}
