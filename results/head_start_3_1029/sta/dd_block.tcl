# ---- HEAD-START-3 addition: full path report per D endpoint (max + min) for the launch CLK -> D data delay
foreach p [get_pins -of_objects $ff -filter "direction==input"] {
  set n [get_full_name $p]
  if {![string match */D $n]} {continue}
  report_checks -to $p -path_delay max -format full -digits 3 >> /out/ddmax_$::env(CORNER).rpt
  report_checks -to $p -path_delay min -format full -digits 3 >> /out/ddmin_$::env(CORNER).rpt
}
