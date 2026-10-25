# PATH-QC-N59 LEC: gold = main qfd_native59_qbank (per-bit-mask macro); gate = the 16-lane-enable qbank (gate.v, written
# by gen_gate.ys through the slang frontend) with the macro reached through n59_mask16_shim.
export DESIGN_NAME = qfd_native59_qbank
export VERILOG_FILES = /work/old_qbank.sv
export VERILOG_TOP_PARAMS = QB_ALIGN 1 QB_LOCAL32 1
export ADDITIONAL_LIBS = /work/old_macro_tt.lib
export SYNTH_HDL_FRONTEND = slang
