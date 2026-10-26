# N59 reset-load granularity: qfd_n59_kreg_r is an exact W-bit register wrapper.
# Keeping its hierarchy hides W per-bit reset loads from ot_rst_copies; one coarse
# wrapper input was split as one load, later mapped to W distant SRAM-pin flops.
# Flatten ONLY this wrapper before the standard per-bit keep/reset-copy hook.
# Function and edge count are unchanged; kept register wires remain preserved.
yosys select -set n59_rst_wrap {*qfd_n59_kreg_r*}
set n59_rst_mods [string trim [yosys tee -q -s result.string select -list @n59_rst_wrap]]
if {$n59_rst_mods eq ""} { error "N59 reset-wrapper flatten found no modules" }
# Transfer the wrapper's physical copy-preservation intent to its Q wire
# before removing the boundary. Without this, 2,951 resettable capture FFs
# folded (44,719 -> 41,768 actual FFs), exactly the lost reset-pin count.
yosys select -set n59_rst_q {*qfd_n59_kreg_r*/w:q}
set n59_rst_qnames [string trim [yosys tee -q -s result.string select -list @n59_rst_q]]
if {$n59_rst_qnames eq ""} {error "N59 reset wrapper Q keep selected no wires"}
yosys setattr -set keep 1 @n59_rst_q
yosys setattr -mod -unset keep_hierarchy @n59_rst_wrap
yosys select -clear
yosys flatten
yosys opt_clean
puts "N59 reset wrappers expanded before per-bit regional reset splitting"
