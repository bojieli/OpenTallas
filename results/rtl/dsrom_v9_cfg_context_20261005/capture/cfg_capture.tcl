set c $::env(CFG_CORNER)
set l /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list asap7sc7p5t_AO_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${c}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${c}_nldm_220123.lib] {read_liberty $l/$f}
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_[string tolower $c].lib
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.lef
read_verilog /input/results/asap7/copernicus_cfg_provider/base/1_2_yosys.v
link_design ot_v41_pair_cfgrom_context
read_sdc /input/constraint.sdc
set_units -time ps -capacitance fF
set block [ord::get_db_block]
set macro [$block findInst g_hard_cfg.u_cfg]
if {$macro eq "NULL" || [[$macro getMaster] getName] ne "ot_rom_4096x72_m8"} {error "real cfg macro absent"}
set clocks [get_clocks -quiet core_clk]
if {[llength $clocks] != 1} {error "retained root clock absent"}
set source [get_cells -quiet g_hard_cfg.u_cfg]
set capture [all_registers -clock core_clk -data_pins]
foreach mode {min max} {
    if {![llength [find_timing_paths -from $source -to $capture -path_delay $mode -group_count 1]]} {
        error "actual cfg macro-to-loader $mode capture path absent"
    }
    report_checks -from $source -to $capture -path_delay $mode -group_count 48 \
      -format full_clock_expanded -fields {slew capacitance input_pin net} > /out/${c}_cfg_capture_${mode}.rpt
}
report_clock_properties $clocks > /out/${c}_clocks.rpt
puts "CFG_CAPTURE_PATH_PASS $c PRE_CTS_RETAINED_DECK_NO_PARASITICS"
