#!/bin/bash
# usage: red_eq.sh tag N SL MLAT ALAT RPAD RSL RTAP NCYC
R=/srv/opentallas-scratch2/scratch/claude/hbm-su/red/r7; cd $R/src
tag=$1; N=$2; SL=$3; M=$4; A=$5; P=$6; S=$7; T=$8; NC=$9; RO=${10:-0}; G=${11:-4}
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
O=$R/eq/$tag; mkdir -p $O
SRC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/test/ot_ref_vec_red.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv rtl/test/tb_hdc_v41x_vec_red_c12.sv"
$V --cc --exe --build -j 16 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hdc_v41x_vec_red_c12 -GN=$N -GSL=$SL -GMLAT=$M -GALAT=$A -GRPAD=$P -GRSL=$S -GRTAP=$T -GROUT=$RO -GROGS=$G \
  -Mdir $O/obj $SRC rtl/test/tb_hdc_v41x_vec_red_c12.cpp -CFLAGS -O1 > $O/build.log 2>&1 || { echo "build_rc=$?" > $O/rc; exit 1; }
$O/obj/Vtb_hdc_v41x_vec_red_c12 +NCYC=$NC > $O/run.log 2>&1; rc=$?
echo "rc=$rc" > $O/rc; tail -3 $O/run.log
exit $rc
