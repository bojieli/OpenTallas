yosys read_verilog -sv rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_wdecode_local_status.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v
yosys hierarchy -top ot_vms_bank_static_wdecode_local_status -chparam RG 4 -chparam WG 1
source ot_keep_regs.tcl
yosys synth -top ot_vms_bank_static_wdecode_local_status -noabc
yosys write_json local_status_synth.json
