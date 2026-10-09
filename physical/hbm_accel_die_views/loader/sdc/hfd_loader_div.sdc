# hfd_loader L-DIV (stream ingest 2026-10-08; rtl/ot_hfd_loader_div.sv): the core runs on ckd = ck / 2 from the divider flop
# u_ld.ckd (its own clock root, no gating).  Every core <-> face crossing is a Gray-pointer async FIFO, so ckd and core_clk
# are asynchronous groups (no multicycle set: the core is single-cycle at 2 x the die period).  Fails loudly if the divider
# net is not found (an unclocked core would read as closed).
set ot_ckd_pins [get_pins -quiet -of_objects [get_nets -quiet {u_ld.ckd}] -filter "direction == output"]
if {[llength $ot_ckd_pins] == 0} { set ot_ckd_pins [get_pins -quiet -hierarchical {u_ld.ckd*/Q}] }
if {[llength $ot_ckd_pins] == 0} { error "OT_LOADER_DIV: divider output u_ld.ckd not found" }
set ot_cksrc [get_ports -quiet ck]
if {[llength $ot_cksrc] == 0} { set ot_cksrc [get_ports {ck[0]}] }
create_generated_clock -name ckd -source $ot_cksrc -divide_by 2 $ot_ckd_pins
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks ckd]
puts "OT_LOADER_DIV generated clock ckd on [llength $ot_ckd_pins] pin(s), asynchronous to core_clk"
