#!/bin/bash
# usage: run_nf.sh OUT [iverilog defines...]; cwd repo, gold form = main 4a4356e476f (pre FORM-NF)
W=$PWD; O=$1; shift; mkdir -p $O; cd $O
F=rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv
git -C $W show 4a4356e476f:$F | awk '/^module ot_s81dv_norm_finish/{p=1} p{print} p&&/^endmodule/{exit}' | sed 's/module ot_s81dv_norm_finish/module gold_nf/' > gold.sv
awk '/^module ot_s81dv_norm_finish/{p=1} p{print} p&&/^endmodule/{exit}' $W/$F > new.sv
S=$(cd $W; for m in rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv; do echo $W/$m; done)
iverilog -g2012 "$@" -o sim -s tb $W/rtl/test/s81_lec_xfin/tb_nf.sv gold.sv new.sv $S 2>&1 | grep -iv warn | head -20
for s in 1 2 3; do timeout 280 vvp -n sim +seed=$s | grep -E "NF_LAT|MISMATCH|EXTRA" | head -4; done
