export DESIGN_NAME = ot_ta_add_bf16_sram_engine
export DESIGN_NICKNAME = opentallas_qwen_add_sram
export PLATFORM = ihp-sg13g2

export VERILOG_FILES = /work/rtl/ot_ta_command_decoder.sv \
                       /work/rtl/ot_bf16_add_rne.sv \
                       /work/rtl/ot_ta_add_bf16_executor.sv \
                       /work/rtl/ot_ta_add_bf16_sram_engine.sv
export SDC_FILE = /work/physical/ihp_sg13g2_qwen_rtl/add_sram/constraint.sdc

export CORE_UTILIZATION = 25
export PLACE_DENSITY = 0.55
export TNS_END_PERCENT = 100
export CTS_BUF_DISTANCE = 60
export HOLD_SLACK_MARGIN = 0.10
export MAX_ROUTING_LAYER = Metal5
export CORNERS = slow typ fast
export USE_FILL = 1

# The ORFS image auto-enables its bundled Kepler LEC executable when present.
# That optional child binary raises SIGILL on this host, after CTS itself has
# completed.  Keep it out of this public-PDK feasibility flow; the retained
# campaign must report that Kepler LEC was not run.
export LEC_CHECK = 0
