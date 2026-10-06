read_liberty {/tmp/ot-links-readonly-inputs/lib/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz}
read_liberty {/tmp/ot-links-readonly-inputs/lib/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz}
read_liberty {/tmp/ot-links-readonly-inputs/lib/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz}
read_liberty {/tmp/ot-links-readonly-inputs/lib/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib}
read_liberty {/tmp/ot-links-readonly-inputs/lib/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz}
read_db {/tmp/ot-links-readonly-inputs/base/6_final.odb}
read_sdc {/tmp/ot-links-readonly-inputs/base/6_final.sdc}
read_spef {/tmp/ot-links-readonly-inputs/base/6_final.spef}
set_propagated_clock [all_clocks]
set_units -time ps -capacitance fF
set b [ord::get_db_block]
set f [open {/tmp/ot-codex-hbm-links-20261006/physical/hbm_die_abstracts_20261006/links/meso_w512_d4_r2/pins_ss.tsv} w]
puts $f "port\tdirection\tnet\treceiver_pin_cap_fF\tloads"
foreach bt [$b getBTerms] {
 set net [$bt getNet];set cap 0;set loads {}
 if {$net ne "NULL"} {
  foreach it [$net getITerms] {
   if {[$it isOutputSignal] || [[$it getMTerm] getSigType] in {POWER GROUND}} {continue}
   set ref [[[$it getInst] getMaster] getName];set pin [[$it getMTerm] getName]
   set lp [get_lib_pins -quiet */$ref/$pin]
   if {[llength $lp]!=1} {error "missing actual sink Liberty $ref/$pin"}
   set cp [get_property $lp capacitance];set cap [expr {$cap+$cp}]
   lappend loads [list [[$it getInst] getName] $ref $pin $cp]
  }
 }
 puts $f [join [list [$bt getName] [$bt getIoType] [$net getName] $cap $loads] "\t"]
}
close $f
redirect {/tmp/ot-codex-hbm-links-20261006/physical/hbm_die_abstracts_20261006/links/meso_w512_d4_r2/clock_paths_ss.txt} {
 report_checks -path_delay min_max -to [all_outputs] -group_path_count 8 -format full_clock_expanded
}
write_timing_model -library_name ot_meso_fifo_ss {/tmp/ot-codex-hbm-links-20261006/physical/hbm_die_abstracts_20261006/links/meso_w512_d4_r2/ot_meso_fifo_ss.lib}
write_abstract_lef {/tmp/ot-codex-hbm-links-20261006/physical/hbm_die_abstracts_20261006/links/meso_w512_d4_r2/ot_meso_fifo.lef}
puts OT_EXPORT_DONE
exit
