#!/bin/bash
# hbm-phys [svc] 2026-10-10: svc-side DMA stream v2 gate (tb/tb_svd2_stack.sv: ot_svd_stack = request unit + 32 PC units
# + 8 group units against tb_svd_phy, 32 in-order PC models at 0.7716 sector/cycle each = 3.80 TB/s a die).
#   run_bench_dma.sh <out>      (run from the source snapshot root; SVD_SIM=iverilog = four-state)
#   rand_s1..3   random requests (tag, nsec 1..256, any address), PHY latency 20..60 / 5..125, credits 32 / 4:
#                every sector of every request exactly once, on its PC's lane, data exact, never without a credit: PASS
#   bw_lat54/104 256-sector requests back to back, 16 tags, CR0 32 credits returned 25 cycles after the beat (the front's
#                5-cycle land/pop/credit + 2 x 10 die hops, hgi-1010/c): steady rate >= 22.3 sectors/cycle a stack
#                (90 % of 792 B/cycle) at PHY latency 44..64 and 90..120
#   neg_rdy      mutant: kr_rdy held high (no lane-credit backpressure) -> must FAIL
#   neg_pc       mutant: the owned-row hash drops r[14:10] -> must FAIL
#   neg_mask     mutant: sectors outside the request are sent -> must FAIL
#   neg_room     mutant: the request unit ignores the PCs' queue room (QD 4) -> must FAIL
set -u
O=$1; mkdir -p $O; V=physical/hbm_accel_die_views/svc
rm -f $O/summary.txt
LIB="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv $V/rtl/ot_hbm_svc_core.sv $V/rtl/ot_hbm_svc_seg_lib.sv"
PSL=$V/rtl/ot_hbm_svc_ps_lib.sv; DML=$V/rtl/ot_hbm_svc_dma_lib.sv
sed "s/      kr_rdy_o <= (DMA == 0) || (lcr_n >= CW'(2));/      kr_rdy_o <= 1'b1;/" $PSL > $O/ps_mut_rdy.sv
sed "s/  wire \[27:0\] rc = {bk, 5'(PCID) ^ bk\[4:0\] ^ bk\[9:5\]};/  wire [27:0] rc = {bk, 5'(PCID) ^ bk[4:0]};/" $PSL > $O/ps_mut_pc.sv
sed "s/  wire dkeep = dmh\[bb_r\[1:0\]\];/  wire dkeep = 1'b1;/" $PSL > $O/ps_mut_mask.sv
sed "s/  wire room = .*/  wire room = 1'b1;/" $DML > $O/dma_mut_room.sv
rc=0
for m in "ps_mut_rdy $PSL" "ps_mut_pc $PSL" "ps_mut_mask $PSL" "dma_mut_room $DML"; do set -- $m; cmp -s $O/$1.sv $2 && { echo "$1 not applied" >> $O/summary.txt; rc=1; }; done
sim() {   # sim <label> <ps lib> <dma lib> <runtime args> <defines...>
  local L=$1 P=$2 D=$3 R=$4; shift 4
  if [ "${SVD_SIM:-verilator}" = iverilog ]; then
    iverilog -g2012 "$@" -o $O/$L.vvp -s tb_svd2_stack $LIB $P $D $V/tb/tb_svd2_stack.sv > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; return 3; }
    vvp -n $O/$L.vvp > $O/$L.log 2>&1
  else
    verilator --binary --timing -j 4 -Wno-fatal "$@" --top-module tb_svd2_stack --Mdir $O/vlt_$L $LIB $P $D $V/tb/tb_svd2_stack.sv > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; return 3; }
    $O/vlt_$L/Vtb_svd2_stack $R > $O/$L.log 2>&1
  fi
}
BW="-DBW -DNREQ=300 -DCR0=32 -DCRD=25"
sim rand_s1 $PSL $DML +verilator+seed+1 -DNREQ=400 &
sim rand_s2 $PSL $DML +verilator+seed+2 -DNREQ=400 -DLAT_MIN=5 -DLAT_SPAN=120 &
sim rand_s3 $PSL $DML +verilator+seed+3 -DNREQ=400 -DCRD=30 -DCR0=4 &
sim bw_lat54 $PSL $DML +verilator+seed+1 $BW -DLAT_MIN=44 -DLAT_SPAN=20 &
sim bw_lat104 $PSL $DML +verilator+seed+1 $BW -DLAT_MIN=90 -DLAT_SPAN=30 &
sim neg_rdy $O/ps_mut_rdy.sv $DML +verilator+seed+1 $BW -DLAT_MIN=44 -DLAT_SPAN=20 -DCR0=4 -DTMO=60000 &
sim neg_pc $O/ps_mut_pc.sv $DML +verilator+seed+1 -DNREQ=100 -DTMO=60000 &
sim neg_mask $O/ps_mut_mask.sv $DML +verilator+seed+1 -DNREQ=100 -DTMO=60000 &
sim neg_room $PSL $O/dma_mut_room.sv +verilator+seed+1 -DNREQ=400 -DQD=4 -DLAT_MIN=60 -DLAT_SPAN=60 -DTMO=60000 &
wait
for L in rand_s1 rand_s2 rand_s3 bw_lat54 bw_lat104; do
  grep -q "^SVD2_STACK PASS" $O/$L.log; r=$?
  if [[ $L == bw_* ]]; then
    p=$(grep -o 'steady rate=[0-9.]*' $O/$L.log | cut -d= -f2)
    awk -v p="${p:-0}" 'BEGIN{exit !(p >= 22.3)}' || r=1
  fi
  echo "$L rc=$r $(grep -E '^SVD2_STACK (requests|steady)' $O/$L.log | tr '\n' ' ')" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
done
for L in neg_rdy neg_pc neg_mask neg_room; do
  grep -q "^SVD2_STACK PASS" $O/$L.log && r=0 || r=1
  echo "$L rc=$r (must be nonzero) $(grep -m1 -E 'ERR' $O/$L.log)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
done
echo "DMA_GATE rc=$rc" >> $O/summary.txt
cat $O/summary.txt
exit $rc
