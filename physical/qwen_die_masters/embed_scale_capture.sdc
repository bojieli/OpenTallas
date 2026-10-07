# Each ROM is enabled only every second edge. Its sole load is capture's
# clock-enabled capture, two edges after that ROM launch. No IO or control
# path is relaxed. The transaction bench checks the actual two-edge cadence.
set eb_rom_outputs [get_pins -hierarchical -quiet {u_scale/rd_out*}]
if {[llength $eb_rom_outputs] != 266} {
  error "embedding bank needs exactly 266 real ROM output pins, got [llength $eb_rom_outputs]"
}
set_multicycle_path 2 -setup -from $eb_rom_outputs
set_multicycle_path 1 -hold -from $eb_rom_outputs
