# PG-ACTIVITY-4 (10-27) independent KV below-M7 re-solve on kv3_head_eighth_e1 (signed 6_final.odb, NO pdngen -ripup:
# PG-ACTIVITY-3 found ripup regeneration to be a method artefact on QC). Its signed core PDN (M1/M2 follow-pins + M5
# 0.12@4.32) is kept byte-for-byte; the plan partition straps (tools/die_plan/gen_phys.py PDN: M6 0.288@4.32 off 1.968,
# M7 0.288@8.64 off 4.128, M5-M6 + M6-M7 vias) are ADDED on top. Loads = OpenSTA per-instance power with the measured
# e1 activity (act.txt, kv_core_power_meas.tcl annotation). -source_type FULL: every M7 node ideal = the split point of
# the above-M7 (M7..M9 + bumps) deck, so M7 lateral spreading is NOT counted here.
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_tt.lib /work/macros/*_typ.lib] { read_liberty $f }
read_db /work/odb/6_final.odb
read_sdc /work/odb/6_final.sdc
read_spef /work/odb/6_final.spef
set_propagated_clock [all_clocks]
set b [ord::get_db_block]
puts "KVB_DIE [[$b getDieArea] xMax] [[$b getDieArea] yMax] insts [llength [$b getInsts]]"
foreach nn {VDD VSS} { set n [$b findNet $nn]; set c 0; foreach sw [$n getSWires] { incr c [llength [$sw getWires]] }; puts "KVB_SWIRES_BEFORE $nn $c" }
if {$::env(KVB_ACT) ne "none"} {
set fh [open /work/act.txt r]
while {[gets $fh ln] >= 0} { set A([lindex $ln 0]) [lindex $ln 1] }
close $fh
proc norm {n} { regsub {\$_.*$} $n {} k; regsub -all {/} $k {.} k; regsub {^\\} $k {} k; return $k }
set nm 0; set nu 0; set sum 0.0
set regs [all_registers -edge_triggered]
foreach r $regs { set n [get_full_name $r]; set k [norm $n]; if {[info exists A($k)]} { set R($n) $A($k); incr nm; set sum [expr {$sum + $A($k)}] } }
set def [expr {$nm ? $sum / $nm : 0.5}]
foreach r $regs { set n [get_full_name $r]; if {[info exists R($n)]} { set a $R($n) } else { set a $def; incr nu }
  foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $a -duty 0.5 } }
foreach p [all_inputs -no_clocks] { set n [get_full_name $p]; regsub {^g_t_([0-9]+)_(u_[a-z0-9]+)__(.*)$} $n {u_g_t_\1_\2.\3} k
  if {[info exists A($k)]} { set a $A($k) } else { set a $def }; set_power_activity -input_ports $p -activity $a -duty 0.5 }
puts "KVB_REG_MATCHED $nm KVB_REG_DEFAULT $nu"
}
report_power -digits 6
# capture the measured per-instance STA power BEFORE pdngen/setRC (setRC resets STA so PSM's own query charges 0.182 W
# regardless of activity -- shown by this lane's meas vs vless probes); apply it explicitly below.
set scn [sta::cmd_scene]; set tot 0.0; set ni 0
foreach inst [get_cells *] { set p [lindex [sta::instance_power $inst $scn] 3]
  if {$p > 0} { set IP([[sta::sta_to_db_inst $inst] getName]) $p; set tot [expr {$tot + $p}]; incr ni } }
puts "KVB_INST_POWER_CAPTURED $ni total_W $tot"
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {part} -voltage_domains {CORE}
add_pdn_stripe -grid {part} -layer {M6} -width {0.288} -spacing {0.096} -pitch {4.32} -offset {1.968}
add_pdn_stripe -grid {part} -layer {M7} -width {0.288} -spacing {0.096} -pitch {8.64} -offset {4.128}
add_pdn_connect -grid {part} -layers {M5 M6}
add_pdn_connect -grid {part} -layers {M6 M7}
pdngen
foreach nn {VDD VSS} { set n [$b findNet $nn]; set c 0; foreach sw [$n getSWires] { incr c [llength [$sw getWires]] }; puts "KVB_SWIRES_AFTER $nn $c" }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
# FULL put the ideal sources on the core's M5 PG pins (EM: 0 A through M5-M6/M6-M7). Move the VDD/VSS pins to the M7
# straps: drop the M5 bpins, add one bpin per M7 strap wire, so FULL sources = M7 (the above-M7 deck's split point).
set tech [ord::get_db_tech]; set m7 [$tech findLayer M7]
foreach nn {VDD VSS} {
  set n [$b findNet $nn]; set bt [$n get1stBTerm]; if {$bt eq "NULL"} { set bt [odb::dbBTerm_create $n $nn] }
  foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp }
  set k 0
  foreach sw [$n getSWires] { foreach w [$sw getWires] { if {![$w isVia] && [$w getTechLayer] eq $m7} {
    set bp [odb::dbBPin_create $bt]; odb::dbBox_create $bp $m7 [$w xMin] [$w yMin] [$w xMax] [$w yMax]; $bp setPlacementStatus FIRM; incr k } } }
  puts "KVB_M7_PINS $nn $k"
}
# NOTE (this lane, EM-checked): in this OpenROAD build set_pdnsim_inst_power is ADDED to PSM's own STA instance power
# (M6-M7 source current 0.4265 A = (0.1168 + 0.1817 W)/0.7). KVB_NOEXP=1 solves the STA-only part for exact superposition.
set tot2 0.0; if {![info exists ::env(KVB_NOEXP)]} { foreach n [array names IP] { set_pdnsim_inst_power -inst $n -power $IP($n); set tot2 [expr {$tot2 + $IP($n)}] } }
puts "KVB_INST_POWER_SET [array size IP] total_W $tot2"
foreach nn {VDD VSS} { if {[catch {check_power_grid -net $nn} e]} { puts "KVB_PG_CHECK_FAIL $nn $e" } else { puts "KVB_PG_CHECK_OK $nn" } }
foreach nn {VDD VSS} {
  if {[catch {analyze_power_grid -net $nn -source_type FULL -voltage_file /work/out/ir_$nn.csv -error_file /work/out/err_$nn.rpt -enable_em -em_outfile /work/out/em_$nn.csv} e]} { puts "KVB_PSM_FAIL $nn $e" } else { puts "KVB_PSM_OK $nn" }
}
exit
