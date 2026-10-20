#!/usr/bin/env bash
# S81-CTRL-SVC svc_rs landing-SRAM bench: $1 variant (base|mut6), $2 ST, $3 PMEM_E, $4 cases; src 5d9c4ecaa, -DOT_SVC_LAND_SRAM
S=/srv/opentallas-scratch/claude/svc-land
V=$1; ST=$2; PE=$3; shift 3
W=$S/src_${V}_s${ST}_pe${PE}; rm -rf $W; mkdir -p $W $S/out && tar xf $S/src_5d9c4ecaa.tar -C $W || exit 1
[ -d $S/vec ] || { mkdir -p $S/vec && tar xf $S/vec.tar -C $S; }
cd $W || exit 1
export DIE=0 ST PMEM_E=$PE JOBS=6 RS_XDEF=OT_SVC_LAND_SRAM MAXCYC=40000
echo "HOST $(hostname) V=$V ST=$ST PMEM_E=$PE start $(date)"
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --version
tools/s81_dv/svc_rs/rs_bench_pl.sh $S/out $S/vec $V || { echo "BUILD FAIL"; exit 1; }
for C in "$@"; do for s in 1 2; do
  SEEDS=$s tools/s81_dv/svc_rs/rs_bench_pl.sh $S/out $S/vec $V $C > $S/out/verdict_${V}_s${ST}_pe${PE}_${C}_$s.txt 2>&1 &
done; done
wait; cat $S/out/verdict_${V}_s${ST}_pe${PE}_*.txt
echo "HOST $(hostname) done $(date)"
