#!/bin/bash
# DRIVE-S81-LEPNH RXOP benches (cwd = src root on the fleet host)
O=${1:-../bench1}; mkdir -p $O
export J=2
( STD_NATIVE32=1 RXOP=1 bash tools/s81_slice/lep_bench.sh $O/lep_nh_none_5 none 5 lep_nh > $O/lep_nh_none_5.out 2>&1 ) &
( STD_NATIVE32=1 RXOP=1 bash tools/s81_slice/lep_bench.sh $O/lep_nhr_none_7 none 7 lep_nhr > $O/lep_nhr_none_7.out 2>&1 ) &
( STD_NATIVE32=1 RXOP=1 bash tools/s81_slice/lep_bench.sh $O/lep_nh_nhacc_5 nhacc 5 lep_nh > $O/lep_nh_nhacc_5.out 2>&1 ) &
( RXOP=1 bash tools/s81_slice/lep_std_phase_bench.sh $O/phase_h0_rxop_none 0 none > $O/phase_h0_rxop_none.out 2>&1 ) &
( RXOP=1 bash tools/s81_slice/lep_std_phase_bench.sh $O/phase_h0_rxop_rxopskew 0 rxopskew > $O/phase_h0_rxop_rxopskew.out 2>&1 ) &
( RXOP=0 bash tools/s81_slice/lep_std_phase_bench.sh $O/phase_h0_none 0 none > $O/phase_h0_none.out 2>&1 ) &
wait
for f in $O/*.out; do echo "== $f"; tail -4 $f; done
