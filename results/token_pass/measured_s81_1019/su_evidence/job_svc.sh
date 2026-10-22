#!/usr/bin/env bash
# TOKSIM-S81/SU: svc_rs 16-slice bench on the RELEASE source 19bf4121e (claude/s81-bind-mu4-1019), default engine (SVCQ_ENG_FG3, as every svc_rs bench), no opt-in defines
# $1 ST, $2 PMEM_E, $3.. cases
S=/srv/opentallas-scratch/claude/toksim-s81-su
ST=$1; PE=$2; shift 2
W=$S/src_svc_s${ST}; rm -rf $W; mkdir -p $W $S/out_svc && tar xf $S/src_slice.tar -C $W || exit 1
[ -d $S/vec ] || { mkdir -p $S/vec && tar xf $S/vec.tar -C $S; }
cd $W || exit 1
export DIE=0 ST PMEM_E=$PE JOBS=6 MAXCYC=40000
echo "HOST $(hostname) ST=$ST PMEM_E=$PE start $(date) src 19bf4121e"
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --version
tools/s81_dv/svc_rs/rs_bench_pl.sh $S/out_svc $S/vec base || { echo "BUILD FAIL"; exit 1; }
for C in "$@"; do for s in 1 2; do
  SEEDS=$s tools/s81_dv/svc_rs/rs_bench_pl.sh $S/out_svc $S/vec base $C > $S/out_svc/verdict_s${ST}_pe${PE}_${C}_$s.txt 2>&1 &
done; done
wait; cat $S/out_svc/verdict_s${ST}_pe${PE}_*.txt
echo "HOST $(hostname) done $(date)"
