# QC-CQB2 s5 PRE_CTS: dont_touch lift of the capture flops (kit hold_budget.tcl, unchanged), then the F5 structured
# clock (shared physical/common_flow/mscts_core.tcl): equal-length trunk -> regional taps, macro clock leaves; TritonCTS
# then builds only the local trees under the tap nets.
source /work/hold_budget.tcl
source /work/cf/mscts_core.tcl
ot_ms_build
