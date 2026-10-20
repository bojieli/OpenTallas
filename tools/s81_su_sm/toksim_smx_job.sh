#!/usr/bin/env bash
# TOKSIM-S81B/SMX: release ot_s81_su_sms (19bf4121e) golden + cycle bench at production shape (16 heads, T 640 / 128)
S=/srv/opentallas-scratch/claude/toksim-s81b-smx
W=$S/src; rm -rf $W; mkdir -p $W && tar xf $S/src.tar -C $W || exit 1
mkdir -p $W/rtl/dsrom_sys/s81_dv/su_sm/test && cp $S/tb_toksim_smx.sv $W/rtl/dsrom_sys/s81_dv/su_sm/test/ || exit 1
O=$S/out; rm -rf $O; mkdir -p $O; cd $W || exit 1
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
echo "HOST $(hostname) start $(date) src 19bf4121e"; $VL --version
sha256sum $S/tb_toksim_smx.sv rtl/dsrom_sys/s81_dv/su_sm/*.sv rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv > $O/sha256.txt
( python3 tools/dsrom_su_softmax.py prep --cases tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl --work $O/cases --lph 16 --stress 6 > $O/prep.log 2>&1; echo "EXIT $?" >> $O/prep.log ) &
S_=rtl
SRCS=("$S_/dsrom_sys/s81_dv/su_sm/test/tb_toksim_smx.sv" "$S_/dsrom_sys/s81_dv/su_sm/ot_s81_su_sms.sv"
  "$S_/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv" "$S_/dsrom_sys/s81_dv/su_sm/ot_s81_su_smh.sv"
  "$S_/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv" "$S_/hdc/ot_hdc_delay.sv" "$S_/hdc/ot_hdc_fastfp_lat_f12.sv"
  "$S_/hdc/ot_hdc_fastfp.sv" "$S_/hdc/ot_hdc_fp32_add_lat.sv" "$S_/hdc/ot_hdc_fp32_f12.sv" "$S_/hdc/ot_hdc_fp32_mul_lat.sv"
  "$S_/hdc/ot_hdc_prefix.sv" "$S_/hdc/ot_hdc_sfu.sv" "$S_/hdc/v41x/ot_dsrom_fp32_add_l6.sv" "$S_/hdc/v41x/ot_dsrom_su_add6.sv"
  "$S_/hdc/v41x/ot_dsrom_su_f12.sv" "$S_/hdc/v41x/ot_dsrom_su_fdiv_f12.sv" "$S_/hdc/v41x/ot_dsrom_su_softmax_add6.sv"
  "$S_/hdc/v41x/ot_dsrom_su_softmax_add.sv" "$S_/hdc/v41x/ot_dsrom_su_softmax_f12r.sv"
  "$S_/hdc/v41x/ot_dsrom_su_softmax_m9.sv" "$S_/hdc/v41x/ot_hdc_v41x_sfu.sv")
SMTX=(-DSU_SMU_T rtl/dsrom_sys/s81_dv/su_sm/dsfd_su_t_smh.sv rtl/dsrom_sys/s81_dv/su_sm/dsfd_su_t_smhq.sv rtl/dsrom_sys/s81_dv/su_sm/dsfd_su_t_smhr.sv rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_sm.sv)
bld() { local n=$1 nh=$2; shift 2
  ( $VL --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_toksim_smx -Mdir $O/obj_$n -j 16 --unroll-count 4 -fno-dfg \
     -GNH=$nh -CFLAGS -O1 "$@" "${SRCS[@]}" > $O/build_$n.log 2>&1; echo "EXIT $?" >> $O/build_$n.log ) & }
bld flat16 16
bld smt16 16 "${SMTX[@]}"
bld flat2 2
wait
tail -3 $O/prep.log $O/build_*.log
runall() { local n=$1
  for d in $O/cases/lph16/*/; do c=$(basename $d); [ -x $O/obj_$n/Vtb_toksim_smx ] || continue
    ( $O/obj_$n/Vtb_toksim_smx +case=$d > $O/run_${n}_$c.log 2>&1 ) &
  done; }
runall flat16; runall smt16; runall flat2
wait
for f in $O/run_*.log; do echo "== $f"; grep -E "^SMX" $f | tail -6; done
echo "HOST $(hostname) done $(date)"
