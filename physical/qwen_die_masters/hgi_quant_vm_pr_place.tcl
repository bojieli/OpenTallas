# el1011-hbm-fq/qvm: ot_hgi_quant_vm_transport_p textbook rebuild -- the one result-FIFO SRAM top centre at the same
# 19.4 um top margin as hgi_quant_vm_pp_place.tcl, for any outline height (the rebuilt outlines are 172.8 / 151.2 um).
set b [ord::get_db_block]
set die [$b getDieArea]
set dbu [$b getDbUnitsPerMicron]
set top [expr {[$die yMax] / double($dbu)}]
set y [expr {round(($top - 97.2) / 0.27) * 0.27}]
set count 0
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]} {
  place_macro -macro_name [$i getName] -location [list 130.68 $y] -orientation R0
  incr count
 }
}
if {$count != 1} {error "hgi_quant_vm_pr_place requires exactly one SRAM: $count"}
