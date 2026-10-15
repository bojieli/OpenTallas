# Conditional native bank contract: the real digital clock owner proposes /3
# high1/low2VCOticks. This file preserves the actual scene period and rising
# edges, and models the short pulse. It grants no PLL frequency or epoch claim.
set ot_vm_core [get_clocks -quiet core_clk]
if {[llength $ot_vm_core] != 1} {error "VM_BANK_WAVEFORM: missing unique core clock"}
set ot_vm_period [get_property $ot_vm_core period]
create_clock -name core_clk -period $ot_vm_period -waveform [list 0 [expr {$ot_vm_period/3.0}]] [get_ports ck]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
if {[info exists ::ot_ref_pre_cts] && !$::ot_ref_pre_cts} {
 set_propagated_clock [get_clocks core_clk]
 # Rebind actual pin-register IO references after recreating the clock.
 read_sdc /src/physical/qwen_die_masters/io_ref_skew.sdc
}
puts "VM_BANK_WAVEFORM period=$ot_vm_period high=[expr {$ot_vm_period/3.0}] low=[expr {2*$ot_vm_period/3.0}] conditional_clock_source_unqualified"
