# PATH-S81/ELEMB 10-25 (elemB_if2e): PRE_CTS = the kit's stage clear (golden SDC latencies kept) + the HBM-CLKSTRUCT
# structured in-core clock (core_density_taps.tcl: port -> CTS trunk -> density taps -> local trees; ROM clk pin on the
# tap of its own interface registers).  Replaces the single-root TritonCTS H-tree whose first branch (139,171)->(139,99)
# crossed rom0 and put the lower half (rom0 IF regs, S/E faces) 52 ps TT behind the upper half (elemB_if2d routed RCX).
source /work/prects_clear.tcl
source /work/core_density_taps.tcl
