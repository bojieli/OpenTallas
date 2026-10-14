source /src/tools/ref_tile/path_classes.tcl
puts "DIAG_BOUNDARY reference=[get_full_name $qdm_ref] Lmax=$qdm_lmax Lmin=$qdm_lmin skew=$ot_sk hold=$ot_hk"
report_checks -path_delay max -group_path_count 4 -endpoint_path_count 1 -format full_clock_expanded -fields {slew capacitance fanout input_pins} -digits 4
exit
