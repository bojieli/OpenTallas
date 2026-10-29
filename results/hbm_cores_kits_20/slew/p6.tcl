set libdir /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty $libdir/$f }
set mode $::env(MODE)
set B $::env(BASE)
if {$mode eq "spef"} {
  read_db $B/6_final.odb; read_sdc $B/6_final.sdc; read_spef $B/6_final.spef
} elseif {$mode eq "grtfinal"} {
  read_db $B/6_final.odb; read_sdc $B/6_final.sdc; source /k/setRC_rcx.tcl; estimate_parasitics -global_routing
} elseif {$mode eq "plfinal"} {
  read_db $B/6_final.odb; read_sdc $B/6_final.sdc; source /k/setRC_rcx.tcl; estimate_parasitics -placement
} else {
  read_db $B/5_1_grt.odb; read_sdc $B/5_1_grt.sdc; source /k/setRC_rcx.tcl; estimate_parasitics -global_routing
}
set_propagated_clock [all_clocks]
set fp [open /o/q_$mode.tsv w]
set f [open /o/nets.txt]; set nets [split [string trim [read $f]] "\n"]; close $f
foreach nn [lrange $nets 0 [expr {$::env(N)-1}]] {
  set net [get_nets -quiet $nn]; if {$net eq ""} continue
  sta::redirect_string_begin; catch {report_net -digits 3 $nn} e; set r [sta::redirect_string_end]; append r $e
  set wc -1; set pc -1
  regexp {Wire capacitance:\s+([-0-9.e]+)} $r -> wc
  regexp {Pin capacitance:\s+([-0-9.e]+)} $r -> pc
  set dn [sta::sta_to_db_net $net]; set wl -1
  catch { set w [$dn getWire]; if {$w ne "NULL"} { set wl [expr {[$w getLength]/1000.0}] } }
  puts $fp "$nn\t$wc\t$pc\t$wl"
}
close $fp
puts "DONE $mode"
