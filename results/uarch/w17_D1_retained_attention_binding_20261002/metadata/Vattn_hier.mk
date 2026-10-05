# Hierarchical Verilation -*- Makefile -*-
# DESCRIPTION: Verilator output: Makefile for hierarchical Verilation
#
# The main makefile Vattn.mk calls this makefile

ifndef VM_HIER_VERILATION_INCLUDED
VM_HIER_VERILATION_INCLUDED = 1

.SUFFIXES:
.PHONY: hier_build hier_verilation hier_launch_verilator
# Libraries of hierarchical blocks
VM_HIER_LIBS := \
  Vot_hdc_v41x_attn_staging_3/libot_hdc_v41x_attn_staging_3.a \
  Vot_hdc_v41x_attn_tile_e/libot_hdc_v41x_attn_tile_e.a \
  Vot_hdc_v41x_attn_merge_6/libot_hdc_v41x_attn_merge_6.a \
  Vot_hdc_qadd/libot_hdc_qadd.a \

hier_build: $(VM_HIER_LIBS) Vattn.mk
	$(MAKE) -f Vattn.mk
hier_verilation: Vattn.mk
# Verilation of hierarchical blocks are executed in this directory
VM_HIER_RUN_DIR := /home/ubuntu/w17work/attnhier
# Common options for hierarchical blocks
VM_HIER_VERILATOR := /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
VM_HIER_INPUT_FILES := \
  /home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn_tile.sv \
  /home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn.sv \
  /home/ubuntu/w17work/attnsrc/ot_hdc_v41x_attn_staging.sv \
  /home/ubuntu/w17work/attnsrc/ot_sram_1r1w_256x256_m2_r2c2.v \
  /home/ubuntu/w17work/attnsrc/ot_hdc_fastfp.sv \

VM_HIER_VERILOG_LIBS := \

# VM_HIER_LAUNCH_VERILATOR_ARGSFILE must be passed as a command argument
hier_launch_verilator:
	$(VM_HIER_VERILATOR) -f $(VM_HIER_LAUNCH_VERILATOR_ARGSFILE)

# Verilate the top module
Vattn.mk: $(VM_HIER_INPUT_FILES) $(VM_HIER_VERILOG_LIBS) Vattn__hierMkArgs.f Vot_hdc_v41x_attn_staging_3/ot_hdc_v41x_attn_staging_3.sv Vot_hdc_v41x_attn_tile_e/ot_hdc_v41x_attn_tile_e.sv Vot_hdc_v41x_attn_merge_6/ot_hdc_v41x_attn_merge_6.sv Vot_hdc_qadd/ot_hdc_qadd.sv 
	@$(MAKE) -C $(VM_HIER_RUN_DIR) -f obj/Vattn_hier.mk hier_launch_verilator \
		VM_HIER_LAUNCH_VERILATOR_ARGSFILE="obj/Vattn__hierMkArgs.f"

# Verilate hierarchical blocks
Vot_hdc_v41x_attn_staging_3/ot_hdc_v41x_attn_staging_3.sv Vot_hdc_v41x_attn_staging_3/Vot_hdc_v41x_attn_staging_3.mk: $(VM_HIER_INPUT_FILES) $(VM_HIER_VERILOG_LIBS) Vot_hdc_v41x_attn_staging_3__hierMkArgs.f 
	@$(MAKE) -C $(VM_HIER_RUN_DIR) -f obj/Vattn_hier.mk hier_launch_verilator \
		VM_HIER_LAUNCH_VERILATOR_ARGSFILE="obj/Vot_hdc_v41x_attn_staging_3__hierMkArgs.f"
Vot_hdc_v41x_attn_staging_3/libot_hdc_v41x_attn_staging_3.a: Vot_hdc_v41x_attn_staging_3/Vot_hdc_v41x_attn_staging_3.mk 
	$(MAKE) -f Vot_hdc_v41x_attn_staging_3.mk -C Vot_hdc_v41x_attn_staging_3 VM_PREFIX=Vot_hdc_v41x_attn_staging_3

Vot_hdc_v41x_attn_tile_e/ot_hdc_v41x_attn_tile_e.sv Vot_hdc_v41x_attn_tile_e/Vot_hdc_v41x_attn_tile_e.mk: $(VM_HIER_INPUT_FILES) $(VM_HIER_VERILOG_LIBS) Vot_hdc_v41x_attn_tile_e__hierMkArgs.f Vot_hdc_qadd/ot_hdc_qadd.sv 
	@$(MAKE) -C $(VM_HIER_RUN_DIR) -f obj/Vattn_hier.mk hier_launch_verilator \
		VM_HIER_LAUNCH_VERILATOR_ARGSFILE="obj/Vot_hdc_v41x_attn_tile_e__hierMkArgs.f"
Vot_hdc_v41x_attn_tile_e/libot_hdc_v41x_attn_tile_e.a: Vot_hdc_v41x_attn_tile_e/Vot_hdc_v41x_attn_tile_e.mk Vot_hdc_qadd/libot_hdc_qadd.a 
	$(MAKE) -f Vot_hdc_v41x_attn_tile_e.mk -C Vot_hdc_v41x_attn_tile_e VM_PREFIX=Vot_hdc_v41x_attn_tile_e

Vot_hdc_v41x_attn_merge_6/ot_hdc_v41x_attn_merge_6.sv Vot_hdc_v41x_attn_merge_6/Vot_hdc_v41x_attn_merge_6.mk: $(VM_HIER_INPUT_FILES) $(VM_HIER_VERILOG_LIBS) Vot_hdc_v41x_attn_merge_6__hierMkArgs.f Vot_hdc_qadd/ot_hdc_qadd.sv 
	@$(MAKE) -C $(VM_HIER_RUN_DIR) -f obj/Vattn_hier.mk hier_launch_verilator \
		VM_HIER_LAUNCH_VERILATOR_ARGSFILE="obj/Vot_hdc_v41x_attn_merge_6__hierMkArgs.f"
Vot_hdc_v41x_attn_merge_6/libot_hdc_v41x_attn_merge_6.a: Vot_hdc_v41x_attn_merge_6/Vot_hdc_v41x_attn_merge_6.mk Vot_hdc_qadd/libot_hdc_qadd.a 
	$(MAKE) -f Vot_hdc_v41x_attn_merge_6.mk -C Vot_hdc_v41x_attn_merge_6 VM_PREFIX=Vot_hdc_v41x_attn_merge_6

Vot_hdc_qadd/ot_hdc_qadd.sv Vot_hdc_qadd/Vot_hdc_qadd.mk: $(VM_HIER_INPUT_FILES) $(VM_HIER_VERILOG_LIBS) Vot_hdc_qadd__hierMkArgs.f 
	@$(MAKE) -C $(VM_HIER_RUN_DIR) -f obj/Vattn_hier.mk hier_launch_verilator \
		VM_HIER_LAUNCH_VERILATOR_ARGSFILE="obj/Vot_hdc_qadd__hierMkArgs.f"
Vot_hdc_qadd/libot_hdc_qadd.a: Vot_hdc_qadd/Vot_hdc_qadd.mk 
	$(MAKE) -f Vot_hdc_qadd.mk -C Vot_hdc_qadd VM_PREFIX=Vot_hdc_qadd

endif  # Guard
