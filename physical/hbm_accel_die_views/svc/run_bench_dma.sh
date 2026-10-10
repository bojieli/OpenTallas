#!/bin/bash
# hbm-phys [svc] 2026-10-10: svc-side DMA stream gate (tb/tb_svd_stack.sv, one stack: mid-strip hub ot_svd_hub, 4 group
# units a side on one inward chain each, 32 PC units with in-order PHY models honouring kr_rdy).   run_bench_dma.sh <out>
#   rand_s<k>      random requests (tag, nsec 1..256, any sector address), random PHY latency 20..60: every lane carries
#                  exactly idx % 8 == l of every request, in order, data = the PHY's, no beat without a credit, no X: PASS
#   bw_lat54/104   bandwidth gate: 256-sector requests back to back, PHY latency 44..64 / 90..120, front credit 64 a lane
#                  returned 60 cycles after the beat: steady (10..90 % of the beats) rate >= 90 % of 8 sectors a cycle
#   neg_gq         mutant: a request may start inside the previous request's last row slot (the WIP stall) -> must FAIL
#   neg_rdy        mutant: kr_rdy held high (no PHY backpressure): a beat without a group slot -> must FAIL
#   neg_half       mutant: lanes read the west half of the ROB for every sector -> must FAIL
# SVD_SIM=iverilog runs four-state (X check) instead of Verilator.  (run from the source snapshot root)
set -u
O=$1; mkdir -p $O; V=physical/hbm_accel_die_views/svc
rm -f $O/summary.txt
LIB="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv $V/rtl/ot_hbm_svc_core.sv $V/rtl/ot_hbm_svc_seg_lib.sv"
PSL=$V/rtl/ot_hbm_svc_ps_lib.sv; DML=$V/rtl/ot_hbm_svc_dma_lib.sv
sed "s/  wire \[GW-1:0\] g0 = gn4 + GW'(a0);/  wire [GW-1:0] g0 = gn + GW'((a0 - gn[1:0]) \& 2'd3);/" $DML > $O/dma_mut_gq.sv
sed "s/      kr_rdy_o <= (DMA == 0) || (dfree >= 4'd2);/      kr_rdy_o <= 1'b1;/" $PSL > $O/ps_mut_rdy.sv
sed "s/    assign lh\[gl\] = ve;/    assign lh[gl] = 1'b0;/" $DML > $O/dma_mut_half.sv
rc=0
for m in "dma_mut_gq $DML" "ps_mut_rdy $PSL" "dma_mut_half $DML"; do set -- $m; cmp -s $O/$1.sv $2 && { echo "$1 not applied" >> $O/summary.txt; rc=1; }; done
sim() {   # sim <label> <ps lib> <dma lib> <runtime args> <defines...>
  local L=$1 P=$2 D=$3 R=$4; shift 4
  if [ "${SVD_SIM:-verilator}" = iverilog ]; then
    iverilog -g2012 "$@" -o $O/$L.vvp -s tb_svd_stack $LIB $P $D $V/tb/tb_svd_stack.sv > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; return 3; }
    vvp -n $O/$L.vvp ${R/+verilator+seed+/+seed=} > $O/$L.log 2>&1
  else
    verilator --binary --timing -j 4 -Wno-fatal "$@" --top-module tb_svd_stack --Mdir $O/vlt_$L $LIB $P $D $V/tb/tb_svd_stack.sv > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; return 3; }
    $O/vlt_$L/Vtb_svd_stack $R > $O/$L.log 2>&1
  fi
}
BW="-DBW -DNREQ=300 -DCR0=64 -DCRD=60"
sim rand_s1 $PSL $DML +verilator+seed+1 -DNREQ=400 &
sim rand_s2 $PSL $DML +verilator+seed+2 -DNREQ=400 -DLAT_MIN=5 -DLAT_SPAN=120 &
sim rand_s3 $PSL $DML +verilator+seed+3 -DNREQ=400 -DCRD=30 -DCR0=4 &
sim bw_lat54 $PSL $DML +verilator+seed+1 $BW -DLAT_MIN=44 -DLAT_SPAN=20 &
sim bw_lat104 $PSL $DML +verilator+seed+1 $BW -DLAT_MIN=90 -DLAT_SPAN=30 &
sim neg_gq $PSL $O/dma_mut_gq.sv +verilator+seed+1 -DNREQ=400 -DTMO=100000 &
sim neg_rdy $O/ps_mut_rdy.sv $DML +verilator+seed+1 $BW -DLAT_MIN=90 -DLAT_SPAN=30 -DTMO=100000 &
sim neg_half $PSL $O/dma_mut_half.sv +verilator+seed+1 -DNREQ=100 -DTMO=100000 &
wait
for L in rand_s1 rand_s2 rand_s3 bw_lat54 bw_lat104; do
  grep -q "^SVD_STACK PASS" $O/$L.log; r=$?
  if [[ $L == bw_* ]]; then
    p=$(grep -o 'steady rate=[0-9.]* sectors/cycle (of 8) = [0-9.]*' $O/$L.log | awk '{print $NF}')
    awk -v p="${p:-0}" 'BEGIN{exit !(p >= 90.0)}' || r=1
  fi
  echo "$L rc=$r $(grep -E '^SVD_STACK (requests|steady)' $O/$L.log | tr '\n' ' ')" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
done
for L in neg_gq neg_rdy neg_half; do
  grep -q "^SVD_STACK PASS" $O/$L.log && r=0 || r=1
  echo "$L rc=$r (must be nonzero) $(grep -m1 -E 'ERR' $O/$L.log)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
done
echo "DMA_GATE rc=$rc" >> $O/summary.txt
cat $O/summary.txt
exit $rc
