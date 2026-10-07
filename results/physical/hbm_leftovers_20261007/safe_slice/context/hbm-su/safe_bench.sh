#!/bin/bash
R=/srv/opentallas-scratch2/scratch/claude/hbm-su; cd $R/src_red14; O=$R/safe_bench; mkdir -p $O
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
SRC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv rtl/hdc/v41x/phys/ot_hdc_v41x_vec_red_c12_phys.sv rtl/test/hbm_su_red_safe/tb_red_safe.sv"
run() { t=$1; shift
  $V --binary -j 16 -Wno-fatal -Wno-lint -Wno-style --unroll-count 4 -fno-dfg --top-module tb_red_safe "$@" -Mdir $O/$t $SRC -CFLAGS -O1 > $O/$t.build 2>&1 || { echo build_rc=$? > $O/$t.rc; return; }
  $O/$t/Vtb_red_safe > $O/$t.log 2>&1; echo rc=$? > $O/$t.rc; }
run pos -GNCYC=20000 & run neg -GNCYC=4000 +define+OT_NEG_RED_PREG & wait
grep -h RED_SAFE $O/pos.log $O/neg.log; cat $O/pos.rc $O/neg.rc
echo done > $O/done
