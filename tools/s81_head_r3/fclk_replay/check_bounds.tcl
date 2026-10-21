# Existing read-only bounds and unchanged complete fclk checks; not global row/overlap certification.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l {SEQ_RVT_TT_nldm_220123.lib INVBUF_RVT_TT_nldm_220122.lib.gz SIMPLE_RVT_TT_nldm_211120.lib.gz} {
    read_liberty $P/lib/NLDM/asap7sc7p5t_$l
}
foreach f [glob /baseline/views/*.lib] {read_liberty $f}
read_db /repair/repaired.odb
source /baseline/cluster_bounds.tcl
source /baseline/die_repeaters.tcl
source /candidate/fclk_audit.tcl
source /repair/old_names.tcl
set f [open /baseline/run.tcl]
set found 0
while {[gets $f line]>=0} {
    if {[string match {set ::ot_die_rep_fclk_data_ports *} $line]} {uplevel #0 $line; incr found}
}
close $f
if {$found != 1} {error "missing/ambiguous original complete-payload contract"}
set bounds [ot_cluster_bounds /work/bounds.json repaired_readonly]
set fclk [ot_die_rep_fclk_audit /work/fclk {n*_fck*} {BUFx8_ASAP7_75t_R}]
puts "HEAD_REPAIRED_READONLY bounds=$bounds fclk=$fclk"
if {$bounds || $fclk} {error "existing read-only checks failed"}
puts HEAD_REPAIRED_READONLY_PASS
