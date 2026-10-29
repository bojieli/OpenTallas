set f [open /out/kit_drt/views/libs.txt];set txt [read $f];close $f
foreach line [split $txt \n] {if {[string match {LIBS_ff=*} $line]} {set libs [string range $line 8 end]}}
foreach l $libs {read_liberty $l}
set R /work/run/results/asap7/hbc_ot_hfd_coll_q2_hard_v8g__ring_ag/base
read_db $R/6_final.odb
read_sdc $R/6_final.sdc
set_propagated_clock [get_clocks clk]
read_spef $R/6_final.spef
set f [open /out/negative_hold_endpoints.tsv w]
foreach p [find_timing_paths -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] {
 puts $f "[get_full_name [get_property $p startpoint]]\t[get_full_name [get_property $p endpoint]]\t[get_property $p slack]"
}
close $f
exit
