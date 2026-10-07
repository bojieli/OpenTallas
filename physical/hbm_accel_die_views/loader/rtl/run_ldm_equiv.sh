#!/bin/bash
# run_ldm_equiv.sh <outdir> [seeds] : transaction-level exactness of ot_hfd_loader_host_m (margin + views-agent
# pipeline) against the unchanged ot_hbm_accel_loader_host (Verilator --timing; tb_loader_m_equiv.sv: MREQ / DMA write streams and every
# CSR except CYCLES), then three negative controls that break the pipeline change and must FAIL.
set -u
O=$1; SEEDS=${2:-"1 2 3"}; NPROG=${NPROG:-40}; mkdir -p $O
L=physical/hbm_accel_die_views/loader/rtl
DEPS="physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hdc/ot_hdc_prefix.sv rtl/hbm_accel/loader/ot_hbm_accel_dma64.sv rtl/gpu_sys/ot_gpu_cdc_fifo.sv rtl/link/ot_link_afifo.sv rtl/hbm_accel/loader/ot_hbm_accel_loader_host.sv rtl/hbm_accel/loader/ot_hbm_accel_loader.sv rtl/hbm_accel/loader/ot_hbm_accel_store.sv"
run() { # name loader store host -> rc
  local n=$1; shift
  for s in $SEEDS; do
    verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -DSEED=$s -DNPROG=$NPROG -DMARGIN_B=1 --top-module tb_loader_m_equiv \
      -Mdir $O/$n.$s.obj -o sim $DEPS "$@" $L/tb_loader_m_equiv.sv > $O/$n.$s.build 2>&1 || { echo "$n seed $s BUILD_FAILED"; grep -m5 -i error $O/$n.$s.build; return 2; }
    $O/$n.$s.obj/sim > $O/$n.$s.log 2>&1; local rc=$?
    echo "$n seed $s rc=$rc $(grep LDM_EQUIV $O/$n.$s.log | tail -1)"
    [ $rc -ne 0 ] && return 1
    grep -q "mismatches=0" $O/$n.$s.log || return 1
  done; return 0; }
run exact $L/ot_hfd_loader_m.sv $L/ot_hfd_store_m.sv $L/ot_hfd_loader_host_m.sv; ex=$?
mut() { local n=$1 f=$2 a=$3 b=$4; sed "s/$a/$b/" $L/$f > $O/$n.$f; cmp -s $O/$n.$f $L/$f && { echo "$n NOT APPLIED"; return 9; }
  local fl="$L/ot_hfd_loader_m.sv $L/ot_hfd_store_m.sv"; fl=${fl/$L\/$f/$O/$n.$f}
  SEEDS=${SEEDS%% *} run $n $fl $L/ot_hfd_loader_host_m.sv; }
mut neg_foh_dir ot_hfd_loader_m.sv 'f_oh <= {f_oh\[VOUT-2:0\], f_oh\[VOUT-1\]}' 'f_oh <= {f_oh[0], f_oh[VOUT-1:1]}'; n1=$?
mut neg_rwv ot_hfd_loader_m.sv 'rw_v <= rq_v \&\& !rq_we' 'rw_v <= rsp_v \&\& !rsp_we'; n2=$?
mut neg_otake ot_hfd_store_m.sv 'if(take)o_d<=h_sel;' 'if(fold)o_d<=h_sel;'; n3=$?
echo "SUMMARY exact_rc=$ex neg_rc=$n1,$n2,$n3 (exact must be 0, each negative 1)"
[ $ex -eq 0 ] && [ $n1 -eq 1 ] && [ $n2 -eq 1 ] && [ $n3 -eq 1 ]
