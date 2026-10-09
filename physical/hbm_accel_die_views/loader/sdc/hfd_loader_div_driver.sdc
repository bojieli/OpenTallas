# Fresh historical L-DIV clock contract; not the selected ND1/ADDR37 facade.
# Source-pinned f8e459542 checkpoint maps ckd to this toggle flop's QN plus
# _522265_/Y inversion. CTS may remove the inverter/logical u_ld.ckd net.
# Bind the real stable sequential output and retain the inversion waveform.
set ot_divider_pin [get_pins -quiet {u_ld.ckd$_DFF_PP0_/QN}]
if {[llength $ot_divider_pin] != 1} {
 error "OT_LOADER_DIV_DRIVER: actual mapped toggle QN pin absent or ambiguous"
}
set ot_cksrc [get_ports -quiet ck]
if {[llength $ot_cksrc] == 0} {set ot_cksrc [get_ports {ck[0]}]}
if {[llength $ot_cksrc] != 1} {error "OT_LOADER_DIV_DRIVER: actual source clock absent or ambiguous"}
if {[llength [get_clocks -quiet ckd]]} {delete_clock [get_clocks ckd]}
create_generated_clock -name ckd -source $ot_cksrc -divide_by 2 -invert $ot_divider_pin
# Retain the original proven FIFO crossing obligation and period; no multicycle.
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks ckd]
puts "OT_LOADER_DIV_DRIVER: real mapped QN root, divided2 inverted waveform; source $ot_cksrc output $ot_divider_pin"
