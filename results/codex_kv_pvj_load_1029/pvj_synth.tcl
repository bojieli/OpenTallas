yosys read_slang --top pvj_probe pvj_probe.sv pvj_candidate.sv ot_hdc_fp32_add_lat.sv ot_hdc_fastfp.sv ot_hdc_prefix.sv
yosys hierarchy -check -top pvj_probe
source ot_keep_regs.tcl
yosys synth -top pvj_probe -flatten -noabc
yosys write_json synth.json
