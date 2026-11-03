export PLATFORM      = asap7
export DESIGN_NAME   = head_pad_fragment
export DESIGN_NICKNAME = $(RUN_NAME)
export VERILOG_FILES = $(RUN_DIR)/src/pad_fragment.sv
export SDC_FILE      = $(COUPON)/constraints.sdc
export CORNER        = TC
export CORE_UTILIZATION = 20
