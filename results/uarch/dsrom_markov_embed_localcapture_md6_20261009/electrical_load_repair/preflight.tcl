set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
set M /evidence/physical/asap7_memory_macros/ot_rom_4096x274_m8
read_lef $M/ot_rom_4096x274_m8.lef
foreach C {TT FF} {
 set libs($C) {}
 foreach l [glob $P/lib/NLDM/*RVT_${C}_*.lib*] {read_liberty $l; lappend libs($C) $l}
 set l $M/ot_rom_4096x274_m8_[string tolower $C].lib
 read_liberty $l; lappend libs($C) $l
}
read_db /evidence/6_final.odb
foreach mode {ss ff} {read_sdc -mode $mode /evidence/constraint.sdc}
define_scene WC -mode ss -liberty $libs(TT)
define_scene BC -mode ff -liberty $libs(FF)
source $P/setRC.tcl
foreach mode {ss ff} {set_mode $mode; write_sdc /receipt/before_$mode.sdc}
set_mode ss
set ot_mm_active 1
source /src/physical/dsrom_markov_lookup_localcapture/electrical_env.tcl
foreach mode {ss ff} {
 set_mode $mode
 write_sdc /receipt/after_$mode.sdc
 puts "OT_OUTPUTS_BEGIN $mode"
 foreach port [all_outputs] {puts "OT_OUTPUT [get_full_name $port]"}
 puts "OT_OUTPUTS_END $mode"
}
set_mode ss
read_spef -corner WC /evidence/6_final.spef
read_spef -corner BC /evidence/6_final.spef
puts OT_ELECTRICAL_BEFORE_REPAIR
report_check_types -max_slew -max_cap -max_fanout -violators
catch {remove_fillers}
foreach bt [[ord::get_db_block] getBTerms] {if {[$bt getIoType] ne "OUTPUT"} {continue}; foreach t [[$bt getNet] getITerms] {if {[$t getIoType] eq "OUTPUT"} {set i [$t getInst]; puts "OUTPUT_DRIVER [$bt getName] [$i getName] [[$i getMaster] getName] status=[$i getPlacementStatus]"}}}
set bm [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
puts "BUFFER_MODEL master=BUFx24_ASAP7_75t_R width=[$bm getWidth] height=[$bm getHeight] outputs=[llength [all_outputs]]"
buffer_ports -outputs -buffer_cell BUFx24_ASAP7_75t_R -max_utilization 60 -verbose
estimate_parasitics -placement
repair_design -verbose -max_utilization 60 -slew_margin 50
detailed_placement
estimate_parasitics -placement
puts OT_ELECTRICAL_AFTER_REPAIR_BEFORE_WRITE
report_check_types -max_slew -max_cap -max_fanout -violators
write_db /receipt/repaired.odb
foreach mode {ss ff} {set_mode $mode; write_sdc /receipt/repaired_$mode.sdc}
puts OT_PREFLIGHT_DONE
