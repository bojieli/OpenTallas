export DESIGN_NICKNAME = codex_hq_input_raw
export DESIGN_NAME = ot_s81ph_hq_in
export PLATFORM = asap7
export VERILOG_FILES = /src/dut_hq_in.sv
export VERILOG_DEFINES = -DSYNTHESIS -DOT_S81PH_HQ_INPUT_RAW
export SDC_FILE = /src/clock.sdc
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_HIERARCHICAL = 0
export CORNER = TC
export ADDER_MAP_FILE =
export ASAP7_USE_VT = RVT
export NUM_CORES = 4
export OT_KEEP_PIN_REGS = 1
export SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl
export OT_RST_LAND = 1
export OT_RST_LAND_STAGES = 2
export OT_PIN_REGS_CLOCK = clk
export OT_PIN_REGS_RESET_PORTS = rst_n
export OT_RST_COPIES_MAX = 32
export OT_RST_LAND_COPIES = rst_n=4
export OT_RST_LAND_FIRST_COPIES = rst_n=1
