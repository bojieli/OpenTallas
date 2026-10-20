read_liberty /proof/toy.lib
read_verilog /proof/toy.v
link_design top
create_clock -name core_clk -period 770 [get_ports clk]
create_clock -name hclk -period 900 [get_ports ckh]
create_generated_clock -name ck_o_fwd -source [get_ports clk] -divide_by 1 [get_ports ck_o]
set_propagated_clock [all_clocks]
write_sdc /proof/baseline.export.sdc
source /proof/clock_family.tcl
ot_cf_refresh
if {[dict get $::ot_cf_master ck_o_fwd] ne "core_clk" || [ot_cf_root ck_o_fwd] ne "core_clk"} {error "lost ancestry"}
puts "ANCESTRY_PASS ck_o_fwd master=core_clk source=clk roots=core_clk,hclk"
exit
