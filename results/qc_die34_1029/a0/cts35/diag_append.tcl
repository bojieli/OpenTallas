# DIE-QC-35 diagnostic only: dump the paths behind OT_HOLD_STRUCTURAL, then fail as the gate does.
rename ot_hold_structural_gate ot_hold_structural_gate_orig
proc ot_hold_structural_gate {} {
  set d /work/diag; file mkdir $d
  set fh [open $d/hold_fail.tsv w]
  puts $fh "slack_ps\tstartpoint\tendpoint\tstart_clock\tend_clock"
  foreach p [ot_hold_paths 200000] {
    set s [get_property $p slack]; if {$s eq "INF" || $s >= 0} continue
    set sc ""; set ec ""
    catch {set sc [get_full_name [get_property $p startpoint_clock]]}
    catch {set ec [get_full_name [get_property $p endpoint_clock]]}
    puts $fh [format "%.2f\t%s\t%s\t%s\t%s" $s [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]] $sc $ec]
  }
  close $fh
  set fh [open $d/hold_worst.rpt w]
  catch {puts $fh [report_checks -path_delay min -scenes BC -group_path_count 3 -format full_clock_expanded -fields {slew cap input_pins} -digits 2]} m; puts $fh $m
  close $fh
  set fh [open $d/setup_ena.rpt w]
  catch {puts $fh [report_checks -path_delay max -group_path_count 3 -format full_clock_expanded -fields {slew cap input_pins fanout} -digits 2]} m; puts $fh $m
  close $fh
  catch {write_db $d/cts_prehold.odb}
  ot_hold_structural_gate_orig
}
