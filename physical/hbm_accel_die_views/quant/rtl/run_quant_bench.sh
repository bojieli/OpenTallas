#!/bin/bash
# run_quant_bench.sh <outdir>: views agent 2026-10-06.  (1) tb_aq_equiv: ot_hfd_actquant_m (MR 1, MLAT 6) vs the
# original ot_hdc_actquant and ot_dsrom_actquant_f12, stream compare (q, e, y, fault per vo); (2) the hfd_quant wrapper
# bench (tb_hfd_quant, lockstep vs a reference core with the same parameters); (3) negative: the scale multiplier
# swapped for the 7-cycle unit (stream misaligned) must FAIL.
set -u
O=$1; mkdir -p $O; Q=physical/hbm_accel_die_views/quant/rtl; NB=${NB:-20000}
HDC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv"
REF="physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv"
vb() { local n=$1 top=$2; shift 2; verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module $top -Mdir $O/$n.obj -o sim "$@" > $O/$n.build 2>&1 || { echo "$n BUILD_FAILED"; grep -m5 -i "%Error" $O/$n.build; return 2; }; $O/$n.obj/sim > $O/$n.log 2>&1; }
vb aq tb_aq_equiv -DNB=$NB -DDUT=ot_hfd_actquant_m '-DDUTP=.MR(1),.MLAT(6)' $HDC $REF $Q/ot_hfd_actquant_m.sv $Q/tb_aq_equiv.sv; a=$?
echo "aq rc=$a $(grep -i -m2 'mism\|PASS\|FAIL' $O/aq.log | tr '\n' ' ')"
vb wrap tb_hfd_quant physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv $HDC $Q/ot_hfd_actquant_m.sv $Q/hfd_quant.sv $Q/tb_hfd_quant.sv; w=$?
echo "wrap rc=$w $(grep -i -m2 'mism\|PASS\|FAIL\|checks' $O/wrap.log | tr '\n' ' ')"
sed 's/ot_hdc_fp32_mul_f12_l6r u (/ot_hdc_fp32_mul_f12_l7 u (/' $Q/ot_hfd_actquant_m.sv > $O/aq_mut.sv
vb neg tb_aq_equiv -DNB=2000 -DDUT=ot_hfd_actquant_m '-DDUTP=.MR(1),.MLAT(6)' $HDC $REF $O/aq_mut.sv $Q/tb_aq_equiv.sv; n=$?
echo "neg rc=$n (must be nonzero) $(grep -i -m2 'mism\|PASS\|FAIL' $O/neg.log | tr '\n' ' ')"
echo "SUMMARY aq=$a wrap=$w neg=$n"
[ $a -eq 0 ] && [ $w -eq 0 ] && [ $n -ne 0 ]
