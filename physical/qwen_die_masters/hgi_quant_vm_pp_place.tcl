# hgi-1010/d5: ot_hgi_quant_vm_transport_p -- the one result-FIFO SRAM (171.3 x 77.8) top centre; the request / response /
# command logic sits below it beside the cmd (bottom), rsp (left) and req (right) pins.  Macro data pins face W / E.
set b [ord::get_db_block]
set count 0
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]} {
  place_macro -macro_name [$i getName] -location {130.68 162.0} -orientation R0
  incr count
 }
}
if {$count != 1} {error "hgi_quant_vm_pp_place requires exactly one SRAM: $count"}
