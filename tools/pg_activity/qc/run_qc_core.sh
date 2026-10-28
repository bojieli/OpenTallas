#!/usr/bin/env bash
# run_qc_core.sh BASEDIR OUTDIR TAG  -> VDD and VSS jobs in parallel (docker, memory-capped)
set -u
K=$1; O=$2; TAG=$3; mkdir -p $O/A $O/B; cp $(dirname $(realpath $0))/qc_core_below_m7.tcl $O/; echo "W6=${W6:-0.288} P6=${P6:-4.32} W7=${W7:-0.288} P7=${P7:-8.64}" > $O/straps.txt
for NN in VDD VSS; do
 docker run --rm --name pga5_${TAG}_$NN -m 40g --cpus 4 -e QCB_NET=$NN -e QCB_W6=${W6:-0.288} -e QCB_P6=${P6:-4.32} -e QCB_W7=${W7:-0.288} -e QCB_P7=${P7:-8.64} -u $(id -u):$(id -g) -v $K:/k:ro -v $O:/o openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /o/qc_core_below_m7.tcl" > $O/log_$NN.txt 2>&1 &
done
wait; echo "EXIT_ALL $(date -Is)" >> $O/log_VDD.txt
