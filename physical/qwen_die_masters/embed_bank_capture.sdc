# Each ROM is enabled only every second edge. Its sole load is o_data's
# clock-enabled capture, two edges after that ROM launch. No IO or control
# path is relaxed. The transaction bench checks the actual two-edge cadence.
set eb_rom_outputs [get_pins -hierarchical -quiet {u_lo/rd_out* u_hi/rd_out*}]
if {[llength $eb_rom_outputs] != 532} {
  error "embedding bank needs exactly 532 real ROM output pins, got [llength $eb_rom_outputs]"
}
set_multicycle_path 2 -setup -through $eb_rom_outputs
set_multicycle_path 1 -hold -through $eb_rom_outputs
