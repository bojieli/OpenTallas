set f [lindex [glob /work/results/asap7/*/base/1_synth.odb] 0]
read_db $f
source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl
ot_hj_fences_install
set b [ord::get_db_block]
set n 0
foreach g [$b getGroups] {if {[string match ot_hj_* [$g getName]]} {incr n [llength [$g getInsts]]}}
if {$n != 59580} {error "HWIN_ASSIGN count $n != 59580"}
puts "HWIN_ASSIGN_PASS exact_mapped_cells=$n groups=13"
write_db /out/assigned.odb
