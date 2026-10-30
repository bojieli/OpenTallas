yosys read_verilog -sv /work/rtl/ot_hdc_delay__su_startup_keep1030.sv /work/rtl/ot_hdc_w11_cut__su_startup_keep1030.sv /work/coupon.sv
yosys hierarchy -check -top coupon
source /work/ot_keep_regs.tcl
yosys synth -top coupon -flatten
yosys write_json /work/kept.json
