export DESIGN_NICKNAME = w2_full219_pc7_ss
export DESIGN_NAME = ot_w2_nc6_protected_completion_reset_quarantine
export PLATFORM = asap7
export VERILOG_FILES = /src/rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv /src/rtl/experimental/w2_nc6_correction_control_split_20261003/ot_w2_nc6_correction_control.sv /src/rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_coded_secondary_reset_quarantine.sv /src/rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_protected_completion_reset_quarantine.sv
export VERILOG_TOP_PARAMS = OPT_EXACT 1 OPT_RESET_QUARANTINE 1 NC 6 MAX_OUT 16 AW 34 CTAGW 32 GENW 4 SIDW 3 PTAGW 35 PC_ID 7
export VERILOG_DEFINES = -DSYNTHESIS
export SDC_FILE = /src/physical/w2_full_controller_synthesis_20261003/constraint.sdc
export SYNTH_SCRIPT = /src/physical/w2_full_controller_synthesis_20261003/capture_synth.tcl
export SYNTH_HDL_FRONTEND = slang
export SYNTH_SLANG_ARGS = --unroll-limit=1000000
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_HIERARCHICAL = 0
export SYNTH_MEMORY_MAX_BITS = 15768
export CORNER = WC
export ASAP7_USE_VT = RVT
export ADDER_MAP_FILE =
export LEC_CHECK = 0
