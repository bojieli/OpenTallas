#!/bin/bash
# DIE-QC-35 KITS: routed LEC of PROG ffh10r 6_final.v against each candidate kit RTL (find the synthesised source)
D=$1; cd $D
for f in cands/*.sv; do n=$(basename $f .sv); T=$D/try_$n; rm -rf $T; mkdir -p $T
  (cd kit_ffh10r && tar --exclude=./lec_routed --exclude=./run -cf - .) | tar -C $T -xf -
  mkdir -p $T/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base; ln kit_ffh10r/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base/6_final.v $T/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base/6_final.v
  cp $f $T/rtl/qfd_dv_s5_vm8x.sv
  OT_LEC_SUPERSET_VEC=1 python3 -I $T/lec.py $T --netlist $T/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base/6_final.v --out $T/lec_routed --mem 40 --jobs 8 > $T/lec_client.log 2>&1
  echo "CAND $n rc $? $(tail -1 $T/lec_client.log | cut -c1-200)"
done
