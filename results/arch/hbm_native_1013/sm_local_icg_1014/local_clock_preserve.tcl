# Own-scope fixed auxiliary commit clock delay; do not alter shared CTS helpers.
set local_delay_cells [get_cells -quiet u_enable_aux_clock_delay_*]
if {[llength $local_delay_cells] != 6} {error "SM_AUX_CLOCK_DELAY_REQUIRED expected6 got[llength $local_delay_cells]"}
set_dont_touch $local_delay_cells
foreach local_c $local_delay_cells {set_dont_touch [get_nets -of_objects [get_pins -of_objects $local_c]]}
puts "SM_AUX_CLOCK_DELAY_PRESERVED [llength $local_delay_cells]"
