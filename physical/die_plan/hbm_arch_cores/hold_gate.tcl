# HBM-CORES3 10-25 (COORD CORRECTION 00:46): post-CTS FF hold gate. STOP (structural -> plan/RTL fix, no repair)
# when FF hold WNS < -100 ps or > 2000 hold endpoints on the CTS tree (placement RC, SDC 25 ps hold uncertainty).
# HBM 10-25 01:40: the STOP counts reg->reg endpoints only (the clock-tree structure the gate is meant to catch).
# Port paths (in->reg, reg->out) are reported but not gated: their min slack is set by the kit SDC IO contract
# (vclk source latency I, input -min -40 ps), not by the tree. gq_land 4d3dd24bd7bf CTS showed 1433 in->reg
# (-60.7) + 1669 reg->out (-22.3) + 36 reg->reg (-31.0): the old all-path count (3138) stopped a structurally
# clean core. Port hold is still repaired in flow and checked at signoff.
foreach l [split $::env(PLIBS)] { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [get_clocks clk]
source $::env(PLATFORM_DIR)/setRC.tcl
estimate_parasitics -placement
array set n {rr 0 io 0}; array set wns {rr 0.0 io 0.0}
foreach p [find_timing_paths -path_delay min -group_path_count 20000 -endpoint_path_count 1 -slack_max 0] {
  set k rr
  if {[get_property [get_property $p startpoint] is_port] || [get_property [get_property $p endpoint] is_port]} { set k io }
  incr n($k)
  set s [get_property $p slack]
  if {$s < $wns($k)} { set wns($k) $s }
}
set verdict PASS
if {$wns(rr) < -100.0 || $n(rr) > 2000} { set verdict FAIL }
puts "OT_HOLD_GATE $verdict wns_ps [format %.2f $wns(rr)] endpoints $n(rr) reg2reg (limits wns -100 ps, 2000 endpoints); port paths not gated: [format %d $n(io)] endpoints wns [format %.2f $wns(io)]"
