# PATH-QC-N59-4 diagnostic: P5 insertion split = trunk (port->sub-tap output) + local (sub-tap->sinks). Read-only P5 inputs.
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
set c $::env(PCORNER); set m [string tolower $c]
foreach f [list $L/asap7sc7p5t_AO_RVT_${c}_nldm_211120.lib.gz $L/asap7sc7p5t_INVBUF_RVT_${c}_nldm_220122.lib.gz $L/asap7sc7p5t_OA_RVT_${c}_nldm_211120.lib.gz $L/asap7sc7p5t_SEQ_RVT_${c}_nldm_220123.lib $L/asap7sc7p5t_SIMPLE_RVT_${c}_nldm_211120.lib.gz /work/macros/ot_sram_1r1w_32x512_m1_${m}.lib] { read_liberty $f }
read_db /out/4_cts.odb
read_sdc /work/3_place.sdc
source /work/setRC_rcx.tcl
unset_clock_latency -clock clk [get_ports {clk clk_t1 clk_t2 clk_t3}]
set_propagated_clock [all_clocks]
estimate_parasitics -placement
source /work/shallow_clock_pad.tcl
set blk [ord::get_db_block]
set f [open /out/actual_subtaps.tsv]; gets $f; set taps {}
while {[gets $f l] >= 0} { lappend taps [lindex [split $l \t] 0] }
close $f
set r [::ot_dtsh_pad::measure $blk $taps]
set fh [open /res/split_$c.tsv w]
puts $fh "tap\ttap_out_ps\tmean_ps\tlocal_ps\tsinks"
foreach t $taps {
  set inst [$blk findInst $t]; set o [::ot_dtsh_pad::sigpin $inst OUTPUT]
  set p [get_pins "$t/[[$o getMTerm] getName]"]; set a [get_property $p arrival_max_rise]
  lassign [dict get $r $t] mean mn mx n
  puts $fh "$t\t[format %.1f $a]\t[format %.1f $mean]\t[format %.1f [expr {$mean-$a}]]\t$n"
}
close $fh; puts SPLIT_DONE; exit
