#!/bin/bash
# red_safe_bench.sh <outdir> <pos|neg> : SAFE reducer lockstep (tb_red_safe, 16 slices + top vs the c12m reference).
# pos = 20,000 cycles, must print RED_SAFE PASS; neg = OT_NEG_RED_PREG (tags one stage short), must FAIL.
O=$1; mode=$2; mkdir -p $O
V=${VERILATOR:-verilator}
SRC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv rtl/hdc/v41x/phys/ot_hdc_v41x_vec_red_c12_phys.sv ${EXTRA_SRC:-} ${TB:-rtl/test/hbm_su_red_safe/tb_red_safe.sv}"
TOP=${TBTOP:-tb_red_safe}
if [ "$mode" = neg ]; then A="-GNCYC=4000 +define+${NEGDEF:-OT_NEG_RED_PREG}"; else A="-GNCYC=${NCYC:-20000}"; fi
$V --binary -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style --unroll-count 4 -fno-dfg --top-module $TOP $A -Mdir $O/obj_$mode $SRC -CFLAGS -O1 > $O/$mode.build 2>&1 || { echo "BUILD_FAILED"; tail -5 $O/$mode.build; exit 2; }
$O/obj_$mode/V$TOP > $O/$mode.log 2>&1; rc=$?
grep -h "RED_" $O/$mode.log | tail -3
exit $rc
