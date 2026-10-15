# Read-only diagnostic: preserve actual post-CTS state before placement verification.
rename check_placement ::sm_diag_real_check_placement
set ::sm_diag_count 0
proc check_placement {args} {
 incr ::sm_diag_count
 set out /work/diag_check_$::sm_diag_count
 write_db ${out}.odb
 write_sdc ${out}.sdc
 foreach corner {WC BC} {
  foreach pd {min max} {
   foreach pin {cgo gout* cgi gin*} {
    set tag [string map {* all} $pin]
    set f ${out}_${corner}_${pd}_${tag}.rpt
    if {[catch {report_checks -corner $corner -path_delay $pd -to [get_ports $pin] -group_count 2 -format full_clock_expanded -fields {slew cap input_pin net fanout} > $f} why]} {
     set fh [open $f w];puts $fh "REPORT_ERROR $why";close $fh
    }
   }
  }
 }
 puts "SM_CTS_DIAG_CAPTURE ${out}"
 return [uplevel 1 [linsert $args 0 ::sm_diag_real_check_placement]]
}
