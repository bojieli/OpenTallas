# Next changed-source opt-in; existing R7 baseline source stays frozen.
include /src/physical/dsrom_wfc_protected_context/body_config.mk
export VERILOG_TOP_PARAMS = ENABLE 1 STRUCTURAL 1 DISTRIBUTED_CMD 1
export WFC_DISTRIBUTED_CMD = 1
