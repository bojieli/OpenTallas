# Repair-only replay of actual failed H1; never calls repair_design/GEN.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l {SEQ_RVT_TT_nldm_220123.lib INVBUF_RVT_TT_nldm_220122.lib.gz SIMPLE_RVT_TT_nldm_211120.lib.gz} {
    read_liberty $P/lib/NLDM/asap7sc7p5t_$l
}
foreach f [glob /baseline/views/*.lib] {read_liberty $f}
read_db /baseline/die_repeaters.fclk.fail.odb
source /baseline/die_repeaters.tcl
source /candidate/fclk_audit.tcl
source /work/old_names.tcl
set found 0
set f [open /baseline/run.tcl]
while {[gets $f line]>=0} {
    if {[string match {set ::ot_die_rep_fclk_data_ports *} $line]} {
        uplevel #0 $line
        incr found
    }
}
close $f
if {$found != 1} {error "missing/ambiguous original complete-payload contract"}
set before [ot_die_rep_fclk_audit /work/before {n*_fck*} {BUFx8_ASAP7_75t_R}]
if {$before != 19} {error "H1 checkpoint does not reproduce actual19 residual hops: $before"}
set n0 [llength [[ord::get_db_block] getInsts]]
set unresolved [ot_die_rep_fclk_equalize /work/repaired {n*_fck*} {BUFx8_ASAP7_75t_R}]
set after [ot_die_rep_fclk_audit /work/after {n*_fck*} {BUFx8_ASAP7_75t_R}]
set n1 [llength [[ord::get_db_block] getInsts]]
puts "H1_REPAIR_ONLY before=$before unresolved=$unresolved after=$after instances_before=$n0 instances_after=$n1"
if {$unresolved || $after} {error "original complete audit remains failed"}
write_db /work/repaired.odb
puts H1_REPAIR_ONLY_PASS
