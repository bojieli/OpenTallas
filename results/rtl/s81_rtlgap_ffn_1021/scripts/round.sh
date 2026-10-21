#!/bin/bash
# RG-FFN round <tag>: census xrt1/xrt3/rstopt + existing XR bench (base hb0/1 x seeds 1-2, mutants) + rstop_sid bench
# (+ tiercol mutant) + transport cut bench (rdpair, mutants 0..11)
T=$1; SL=rtl/dsrom_sys/s81_dv/slice
for t in x1:ot_s81sl_xrt1:ot_s81sl_xrt.sv x3:ot_s81sl_xrt3:ot_s81sl_xrt.sv rs:ot_s81sl_rstopt:ot_s81sl_rstopt.sv; do
  IFS=: read n top f <<< "$t"
  ( ./census.sh ${T}$n $top - rtl/lib/ot_rst_relay.sv $SL/$f 2>&1 | grep -E "^CENSUS|^   [0-9]|^DONE|Chip"; python3 whois.py out_${T}$n 60 ) > c_${T}$n.log 2>&1 &
done
for h in 0 1; do for sd in 1 2; do ./ub_xr.sh $T base $sd $h > b_${T}_base_${sd}_$h.log 2>&1 & done; done
for m in hops row porder nocol xhold; do ./ub_xr.sh $T $m 1 0 > b_${T}_${m}.log 2>&1 & done
./ub_xr.sh $T bwide 1 1 > b_${T}_bwide.log 2>&1 &
( ./ub_rstop.sh $T none; ./ub_rstop.sh $T tiercol ) > b_${T}_rstop.log 2>&1 &
./ub_rdp.sh $T > b_${T}_rdp.log 2>&1 &
wait; for f in c_${T}*.log; do head -12 $f; done; tail -n 3 b_${T}_*.log
