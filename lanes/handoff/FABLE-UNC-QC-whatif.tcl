# FABLE-UNC-QC what-if STA (read-only on the kit): post-CTS timing with the unmeasured tap ports' source window replaced.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [list $P/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz /work/nomcap/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz \
  $P/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz $P/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz \
  /work/nomcap/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz] { read_liberty $l }
foreach l [glob /work/macros/*_tt.lib] { read_liberty $l }
read_db /odb/$::env(ODB)
read_sdc /odb/$::env(SDC)
if {[file exists /work/setRC_rcx.tcl]} { source /work/setRC_rcx.tcl } else { source $P/setRC.tcl }
estimate_parasitics -placement
proc rep {tag} {
  set nmax 0; set nmin 0
  catch { set nmax [sta::endpoint_violation_count max] }
  catch { set nmin [sta::endpoint_violation_count min] }
  puts [format "WHATIF %s setup_ws %.2f setup_tns %.1f n %s | hold_ws %.2f hold_tns %.1f n %s" $tag [sta::worst_slack -max] [sta::total_negative_slack -max] $nmax [sta::worst_slack -min] [sta::total_negative_slack -min] $nmin]
}
rep baseline
# ports with the full window: read the sdc text
set f [open /odb/$::env(SDC)]; set txt [read $f]; close $f
set wide {}
foreach {m e p} [regexp -all -inline {set_clock_latency -source -early (-?[0-9.]+)\s+-clock \[get_clocks \{clk\}\] \[get_ports \{(clk[_a-z0-9]*)\}\]} $txt] {
  if {$e < -150 && [string match clk_t* $p]} { lappend wide $p }
}
puts "WHATIF wide ports [llength $wide]: [lrange $wide 0 5] .."
foreach p $wide {
  set_clock_latency -source -early -20.2 -clock [get_clocks clk] [get_ports $p]
  set_clock_latency -source -late 0.0 -clock [get_clocks clk] [get_ports $p]
}
rep unmeasured_taps_20ps_window
# variant B = QC-DIE-TAPOFF-1 reset form: every glue port (clk, clk_t<k>) at 0 +- 10.1; core ports (clk_c*) untouched
set glue {}
foreach {m p} [regexp -all -inline {set_clock_latency -source -early -?[0-9.]+\s+-clock \[get_clocks \{clk\}\] \[get_ports \{(clk|clk_t[0-9]+)\}\]} $txt] { lappend glue $p }
puts "WHATIF glue ports [llength $glue]"
foreach p $glue {
  set_clock_latency -source -early -10.1 -clock [get_clocks clk] [get_ports $p]
  set_clock_latency -source -late 10.1 -clock [get_clocks clk] [get_ports $p]
}
rep all_glue_ports_0_pm10.1
report_checks -path_delay max -group_path_count 4 -digits 1 -format summary
report_checks -path_delay min -group_path_count 4 -digits 1 -format summary
puts "WHATIF done"
