#!/bin/bash
# REFILL-0730/PROG leg: leg.sh NAME prog|opseg ARGS...   source = claude/mu-die-qw-1019 1f09d70af, Verilator 5.050
set -u; S=/srv/opentallas-scratch/claude/refill-0730/PROG/src_1f09d70af; R=/srv/opentallas-scratch/claude/refill-0730/PROG/run; N=$1; K=$2; shift 2
mkdir -p $R; export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
{ hostname; verilator --version; date; } > $R/$N.out
cd $S
if [ $K = prog ]; then
  python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img results/rtl/qwen_layer_tput_1018/ctlm_prog/image --hard 1 --work $R/prog_$N "$@" >> $R/$N.out 2>&1
else
  bash rtl/test/mu_qwen_seq/run_mu_opseg.sh $R/opseg_$N "$@" >> $R/$N.out 2>&1
fi
rc=$?; date >> $R/$N.out; echo "exit $rc" >> $R/$N.out; exit $rc
