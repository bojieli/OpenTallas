#!/bin/bash
# S81-IDX3R bench builds (run from $S/src on the fleet host): $1 = build name.  Verilator 5.050.
S=${IDX3R_S:-/srv/opentallas-scratch/claude/s81-idx3r-1020}; cd $S/${IDX3R_SRC:-src} || exit 3
C=rtl/dsrom_sys/s81_dv/idx/test/idxrd3_campaign.sh; O=$S/${IDX3R_OUT:-out}; K=results/rtl/s81_idx3r_1020/run_ctrl3.sh
case $1 in
lint) VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
  for t in dsdv_idx_rg3 dsfd_ctrl_rg3; do echo "== $t"
  $VL --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-PINCONNECTEMPTY -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-TIMESCALEMOD --top-module $t \
    rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv \
    rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv \
    rtl/hdc/v41x/ot_hdc_v41x_idx_hslice.sv rtl/hdc/v41x/ot_hdc_v41x_idx_chunk_el.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
    rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv \
    rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv \
    rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg3.sv 2>&1 | grep -E '%(Error|Warning)' | grep -E 'idx_rg3|ctrl_rg3' | head -40; done
  echo LINT_DONE ;;
ctrl) bash $K $O ctrl0 0 \
  "pass_s1|+SEED=1" "pass_s2|+SEED=2" "pass_s3|+SEED=3" "pass_lat60|+SEED=4 +LAT=60" "pass_slothit|+SEED=1 +SLOTHIT=1" ;;
cm1|cm2|cm3) bash $K $O $1 ${1#cm} "fail_s1|+SEED=1" ;;
ctrln) VL_DEF=+define+S81CTRL_NATIVE32 bash $K $O ctrln 0 "pass_s1|+SEED=1" "pass_s2|+SEED=2" "pass_slothit|+SEED=1 +SLOTHIT=1" ;;
cm4) bash $K $O cm4 4 "fail_slothit|+SEED=1 +SLOTHIT=1" ;;
# DRIVE-S81-IDX4-KITS 10-20: the s81ctrl_rg3 kit configuration (SRAM p192 FIFOs, native32): pass + mutant witnesses
ctrls) S81CTRL_FIFO_IMPL=sram_p192 bash $K $O ctrls 0 "pass_s1|+SEED=1" "pass_s2|+SEED=2" "pass_lat60|+SEED=4 +LAT=60" "pass_slothit|+SEED=1 +SLOTHIT=1" ;;
cms1|cms2|cms3) S81CTRL_FIFO_IMPL=sram_p192 bash $K $O $1 ${1#cms} "fail_s1|+SEED=1" ;;
cms4) S81CTRL_FIFO_IMPL=sram_p192 bash $K $O cms4 4 "fail_slothit|+SEED=1 +SLOTHIT=1" ;;
b3) bash $C $O b3 "-GMUT=0 -GSRAM_MACRO=1" 16 \
 "pass_small|+N=4096 +B=13 +T0=400 +P=3" \
 "pass_gs|+GATHER=1 +N=256 +T0=1500 +P=3" \
 "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" \
 "pass_g2048s2|+GATHER=1 +N=2048 +T0=1500 +P=4 +SEED=2" \
 "pass_g2048s3|+GATHER=1 +N=2048 +T0=1500 +P=4 +SEED=3" \
 "closed_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3" \
 "closed_g2048p3s2|+GATHER=1 +N=2048 +T0=1500 +P=3 +SEED=2" \
 "pass_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6" \
 "pass_l2|+N=43691 +B=13 +T0=400 +P=3" \
 "pass_l20|+N=87382 +B=13 +T0=400 +P=3" \
 "pass_l20s2|+N=87382 +B=13 +T0=400 +P=3 +SEED=2" \
 "closed_late|+N=4096 +B=13 +T0=60 +P=3" \
 "closed_glate|+GATHER=1 +N=2048 +T0=60 +P=4" \
 "fail_slothit|+N=4096 +B=13 +T0=400 +P=3 +SLOTHIT=1" \
 "x_t0s200|+N=4096 +B=13 +T0=200 +P=3" \
 "x_gt0s900|+GATHER=1 +N=2048 +T0=900 +P=4" ;;
# DRIVE-S81-IDX4-KITS 10-20: mu7i4 die plan has 23 W->E crossing stations (iq_03_04_l0/l1, is_03_04), b3 used XD 21.
xd23) bash $C $O xd23 "-GMUT=0 -GSRAM_MACRO=1 -GXD=23" 16 \
 "pass_small|+N=4096 +B=13 +T0=400 +P=3" \
 "pass_gs|+GATHER=1 +N=256 +T0=1500 +P=3" \
 "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" \
 "pass_g2048s2|+GATHER=1 +N=2048 +T0=1500 +P=4 +SEED=2" \
 "pass_g2048s3|+GATHER=1 +N=2048 +T0=1500 +P=4 +SEED=3" \
 "closed_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3" \
 "pass_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6" \
 "pass_l2|+N=43691 +B=13 +T0=400 +P=3" \
 "pass_l20|+N=87382 +B=13 +T0=400 +P=3" \
 "pass_l20s2|+N=87382 +B=13 +T0=400 +P=3 +SEED=2" \
 "closed_late|+N=4096 +B=13 +T0=60 +P=3" \
 "closed_glate|+GATHER=1 +N=2048 +T0=60 +P=4" \
 "fail_slothit|+N=4096 +B=13 +T0=400 +P=3 +SLOTHIT=1" \
 "x_t0s200|+N=4096 +B=13 +T0=200 +P=3" \
 "x_gt0s900|+GATHER=1 +N=2048 +T0=900 +P=4" ;;
t0) bash $C $O b3 "-GMUT=0 -GSRAM_MACRO=1" 12 \
 "x_t0s220|+N=4096 +B=13 +T0=220 +P=3" "x_t0s240|+N=4096 +B=13 +T0=240 +P=3" "x_t0s260|+N=4096 +B=13 +T0=260 +P=3" \
 "x_t0s280|+N=4096 +B=13 +T0=280 +P=3" "x_t0s300|+N=4096 +B=13 +T0=300 +P=3" "x_t0s340|+N=4096 +B=13 +T0=340 +P=3" \
 "x_gt0s500|+GATHER=1 +N=2048 +T0=500 +P=4" "x_gt0s600|+GATHER=1 +N=2048 +T0=600 +P=4" "x_gt0s700|+GATHER=1 +N=2048 +T0=700 +P=4" \
 "x_gt0s800|+GATHER=1 +N=2048 +T0=800 +P=4" ;;
sdx) bash $C $O sdx20 "-GMUT=0 -GSRAM_MACRO=1 -GSDX=20" 8 \
 "x_small|+N=4096 +B=13 +T0=400 +P=3" "x_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" "x_l20|+N=87382 +B=13 +T0=400 +P=3" ;;
sd0) bash $C $O sd0 "-GMUT=0 -GSRAM_MACRO=1 -GXD=0" 8 \
 "x_small|+N=4096 +B=13 +T0=400 +P=3" "x_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" "x_l20|+N=87382 +B=13 +T0=400 +P=3" ;;
m1|m3|m4) bash $C $O $1 "-GMUT=${1#m} -GSRAM_MACRO=1" 4 "fail_small|+N=4096 +B=13 +T0=400 +P=3" "fail_g|+GATHER=1 +N=256 +T0=1500 +P=3" ;;
# m2 (budget ignored) / m5 (odd-cell responses lost) act on gather only: a scan job never has 24 requests outstanding on
# a PC lane, and scan reads 2-cell sectors at even cells only.
m2|m5) bash $C $O $1 "-GMUT=${1#m} -GSRAM_MACRO=1" 4 "fail_g|+GATHER=1 +N=256 +T0=1500 +P=3" "fail_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" ;;
m6) bash $C $O m6 "-GMUT=6 -GSRAM_MACRO=1" 4 "fail_open6|+N=4096 +B=13 +T0=400 +P=3 +OPEN=6" ;;
m7) bash $C $O m7 "-GMUT=7 -GSRAM_MACRO=1" 4 "closed_g2048p3|+GATHER=1 +N=2048 +T0=1500 +P=3" "pass_g2048|+GATHER=1 +N=2048 +T0=1500 +P=4" ;;
esac
