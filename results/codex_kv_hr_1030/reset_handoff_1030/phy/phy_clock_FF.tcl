define_corners bc
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc /work/macros/ot_sram_1r1w_512x128_m1_r2c2_ff.lib
read_db /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement

set_propagated_clock [get_clocks clk]
source /work/clk_freeze.tcl
source /work/pg_connect.tcl
ot_pg_connect_all clock_screen
ot_pg_require_bound clock_screen
file mkdir /work/clock_screen
sta::worst_slack_cmd max;sta::worst_slack_cmd min
set cn {};set maxc 0;set capnet {};set cf [open /work/clock_screen/caps_FF.tsv w]
set scene [sta::cmd_scene]
foreach n [ot_clk_dbnets] {
 set name [$n getName];dict set cn $name 1
 set nn [sta::find_net $name]
 if {$nn eq "NULL"} continue
 set cap [expr {[$nn capacitance $scene max]*1e15}]
 puts $cf "$name\t$cap"
 if {$cap>$maxc} {set maxc $cap;set capnet $name}
}
close $cf
set sf [open /work/clock_screen/slews_FF.tsv w];set maxs 0;set slewpin {}
foreach p [get_pins -hier *] {
 set it [sta::sta_to_db_pin $p]
 if {$it eq "NULL" || [$it getNet] eq "NULL" || ![dict exists $cn [[$it getNet] getName]]} continue
 set sl [get_property $p slew_max]
 if {$sl eq "" || ![string is double -strict $sl]} continue
 puts $sf "[get_full_name $p]\t$sl"
 if {$sl>$maxs} {set maxs $sl;set slewpin [get_full_name $p]}
}
close $sf
puts "CLOCK_SCREEN FF nets [dict size $cn] maxcap_fF $maxc net $capnet maxslew_ps $maxs pin $slewpin"
set ::ot_ps_lib_only 1
source /work/pair_skew_current.tcl
unset ::ot_ps_lib_only
ot_ps_zero_unc
set pm [ot_ps_measure 5000]
ot_ps_write $pm /work/clock_screen/pair_FF.tsv FF
puts "CLOCK_PAIR FF counts regs [dict get $pm regs] pairs [dict get $pm pairs] noarrival [dict get $pm no_clock_arrival]"
foreach dly {max min} {puts "CLOCK_PAIR FF $dly [dict get $pm $dly]"}
set vals {};set boundary {};set pub {}
if {[file exists /work/phy_ff_sites.tsv]} {
 set f [open /work/phy_ff_sites.tsv];while {[gets $f line]>=0} {lassign [split $line "\t"] name master x y private;if {!$private} {dict set pub [regsub -all {\\} $name {}] 1}};close $f
}
set f [open /work/clock_screen/arrival_FF.tsv w]
dict for {inst v} $::ot_ps_R {
 lassign $v p clk late early rf
 puts $f "$inst\t$late\t$early\t$rf"
 lappend vals $late
 if {[dict exists $pub [regsub -all {\\} $inst {}]]} {lappend boundary $late}
}
close $f
foreach {label values} [list all $vals public $boundary] {
 if {![llength $values]} continue
 set sorted [lsort -real $values];set sum 0;foreach v $values {set sum [expr {$sum+$v}]}
 puts "CLOCK_INSERTION FF $label n [llength $values] min [lindex $sorted 0] mean [expr {$sum/[llength $values]}] max [lindex $sorted end] spread [expr {[lindex $sorted end]-[lindex $sorted 0]}]"
}
puts CLOCK_SCREEN_DONE_PLACEMENT_OR_MIXED_RC_ONLY_NO_QUALIFICATION
