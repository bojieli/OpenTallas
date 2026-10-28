foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*] { read_liberty $f }
read_liberty /work/macros/ot_rom_4096x266_m8_tt.lib
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
set keys {clk_tb0_d2/Y clkbuf_regs_0_clk/A clkbuf_regs_0_clk/Y clkbuf_0_clk_regs/Y delaybuf_0_clk/A delaybuf_3_clk/Y clkbuf_0_clk/Y u_rom/clk}
proc arr {p} { set a [get_property [get_pins $p] arrival_max_rise]; return $a }
proc meas {tag} {
  global keys
  set s 0; set n 0; set mx -1; set mn 1e9
  foreach p [get_pins -of_objects [all_registers -edge_triggered] -filter "is_clock==1"] {
    set a [get_property $p arrival_max_rise]; if {$a eq "" || [get_full_name $p] eq "u_rom/clk"} continue
    set s [expr $s+$a]; incr n; set mx [expr max($mx,$a)]; set mn [expr min($mn,$a)]
  }
  puts [format "%s flops n %d mean %.1f min %.1f max %.1f" $tag $n [expr $s/$n] $mn $mx]
  foreach k $keys { puts [format "%s %-22s %.1f" $tag $k [arr $k]] }
}
estimate_parasitics -placement
meas PLACE
read_spef /base/6_final.spef
meas SPEF
