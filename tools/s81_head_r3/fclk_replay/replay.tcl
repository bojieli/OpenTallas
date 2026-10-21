# Repair-only replay of an actual failed case; never calls repair_design/GEN.
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
# Compare against the immutable original complete audit, not a caller-supplied count.
set f [open /baseline/die_repeaters.fclk.json]
set baseline_audit [read $f]
close $f
foreach key {mismatch_over_1 hops_judged pairing_errors vacuous} {
    if {![regexp [format {"%s"\s*:\s*([0-9]+)} $key] $baseline_audit -> value]} {error "missing baseline audit $key"}
    set expected($key) $value
}
if {$expected(mismatch_over_1) <= 0 || $expected(hops_judged) <= 0 || $expected(pairing_errors) || $expected(vacuous)} {
    error "baseline is not a complete nonvacuous actual pairing failure"
}
set before [ot_die_rep_fclk_audit /work/before {n*_fck*} {BUFx8_ASAP7_75t_R}]
if {$before != $expected(mismatch_over_1)} {error "checkpoint does not reproduce original residuals: expected=$expected(mismatch_over_1) actual=$before"}
set f [open /work/before.json]
set reproduced_audit [read $f]
close $f
foreach key {hops_judged pairing_errors vacuous} {
    if {![regexp [format {"%s"\s*:\s*([0-9]+)} $key] $reproduced_audit -> value] || $value != $expected($key)} {
        error "checkpoint differs from original complete audit at $key"
    }
}
set n0 [llength [[ord::get_db_block] getInsts]]
set unresolved [ot_die_rep_fclk_equalize /work/repaired {n*_fck*} {BUFx8_ASAP7_75t_R}]
set after [ot_die_rep_fclk_audit /work/after {n*_fck*} {BUFx8_ASAP7_75t_R}]
set n1 [llength [[ord::get_db_block] getInsts]]
puts "HEAD_REPAIR_ONLY before=$before unresolved=$unresolved after=$after instances_before=$n0 instances_after=$n1"
if {$unresolved || $after} {error "original complete audit remains failed"}
write_db /work/repaired.odb
puts HEAD_REPAIR_ONLY_PASS
