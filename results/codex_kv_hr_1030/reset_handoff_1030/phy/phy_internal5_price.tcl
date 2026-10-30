define_corners tc
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc /work/macros/ot_sram_1r1w_512x128_m1_r2c2_tt.lib
read_db /work/output_hold1_fixed/4_cts_outputhold.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set_propagated_clock [get_clocks clk]
set_clock_latency -source 250 [get_clocks vclk]
set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
set ins {};foreach p [all_inputs] {if {![string match ck* [get_full_name $p]]} {lappend ins $p}}
set_input_delay -min -40 -clock [get_clocks vclk] $ins

set targetnames {};set f [open /work/output_hold1_fixed/negative_FF.tsv];while {[gets $f line]>=0} {lassign [split $line "\t"] sp ep sl;dict set targetnames $ep $sl};close $f
set targets {};foreach p [get_pins -hier *] {set n [get_full_name $p];if {[dict exists $targetnames $n]} {dict set targets $n $p}}
if {[dict size $targets]!=5} {error "expected5trueFFnegativepins"}
set f [open /work/output_hold1_fixed/internal5_setup.tsv w]
dict for {ep pin} $targets {
 set ps [find_timing_paths -path_delay max -to $pin -group_path_count 1 -endpoint_path_count 1]
 set worst Inf;foreach p $ps {set worst [expr {min($worst,[get_property $p slack])}]}
 puts $f "$ep\t$worst\t[dict get $targetnames $ep]"
 puts "PHY_INTERNAL5_PRICE $ep TTsetup$worst FFhold[dict get $targetnames $ep]"
}
close $f
puts PHY_INTERNAL5_READONLY_PRICE_DONE
