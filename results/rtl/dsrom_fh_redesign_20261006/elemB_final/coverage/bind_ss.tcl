set_thread_count 1

read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ss.lib
read_db /work/results/asap7/opentallas_ot_dsrom_head_elem_asap7_dshead_elemB_ss_a318fdf47/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_dsrom_head_elem_asap7_dshead_elemB_ss_a318fdf47/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_dsrom_head_elem_asap7_dshead_elemB_ss_a318fdf47/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/dsrom_fh_safe/gen/signoff_elemB.sdc
puts "OT_CORNER ss"
puts "OT_WS [sta::worst_slack_cmd max]"
puts "OT_TNS [sta::total_negative_slack_cmd max]"
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
set n 0; set wd 1e9
foreach p [get_pins -hierarchical */D] { set s [get_property $p slack_max]; if {$s ne "INF"} { if {$s < 0} { incr n }; if {$s < $wd} { set wd $s } } }
puts "OT_VIOL_D_PINS $n"
puts "OT_WS_REG_D $wd"
set wo 1e9
foreach p [all_outputs] { set s [get_property $p slack_max]; if {$s ne "INF" && $s < $wo} { set wo $s } }
puts "OT_WS_OUT $wo"
set pr [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1]
if {[llength $pr]} { puts "OT_WS_R2R [get_property [lindex $pr 0] slack]" } else { puts "OT_WS_R2R INF" }
set pi [find_timing_paths -path_delay max -from [all_inputs] -to [all_registers -data_pins] -group_path_count 1]
if {[llength $pi]} { puts "OT_WS_I2R [get_property [lindex $pi 0] slack]" } else { puts "OT_WS_I2R INF" }

set bind_check max
set count 0
set worst 1e9
foreach pin [all_registers -data_pins] {
  set name [get_full_name $pin]
  if {![string match {u_rom*/*} $name]} continue
  set slack [get_property $pin slack_$bind_check]
  if {![string is double -strict $slack] || $slack eq "INF" || $slack eq "-INF" || $slack != $slack} {
    error "BIND missing finite ss macro slack: $name $slack"
  }
  incr count
  set worst [expr {min($worst,$slack)}]
  puts "OT_BIND_MACRO ss [list $name $slack]"
}
if {$count != 26} { error "BIND expected 26 ROM timing-check pins; got $count" }
if {$worst < 15} { error "BIND macro endpoint misses +15 ps: $worst" }
set nout 0
set nconstant 0
foreach pin [all_outputs] {
  set slack [get_property $pin slack_$bind_check]
  if {![string is double -strict $slack] || $slack eq "INF" || $slack eq "-INF" || $slack != $slack} {
    # JOIN=0 removes A-only result outputs. Exempt only an actual single
    # tie-cell driver in the signed-off ODB, not a name-based whitelist.
    set bt [[ord::get_db_block] findBTerm [get_full_name $pin]]
    set net [$bt getNet]
    set drivers {}
    foreach it [$net getITerms] {
      if {[[$it getMTerm] getIoType] eq "OUTPUT"} {
        lappend drivers [[[$it getInst] getMaster] getName]
      }
    }
    if {[llength $drivers] != 1 || ![regexp {^TIE(LO|HI)x} [lindex $drivers 0]]} {
      error "BIND missing finite output slack: [get_full_name $pin] $slack drivers=$drivers"
    }
    incr nconstant
    puts "OT_BIND_CONSTANT ss [list [get_full_name $pin] [lindex $drivers 0]]"
    continue
  }
  if {$slack < 15} { error "BIND output misses +15 ps" }
  incr nout
}
set period [get_property [get_clocks core_clk] period]
if {abs($period-833.333)>0.001} { error "BIND incorrect signoff period $period" }
write_sdc -no_timestamp /audit/effective_ss.sdc
puts "OT_BIND_DONE ss macro_count $count macro_worst $worst outputs $nout constants $nconstant period $period"
exit
