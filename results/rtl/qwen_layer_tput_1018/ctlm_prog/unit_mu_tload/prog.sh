#!/bin/bash
# MU-DQ-CTLMTL prog bench case: prog.sh NAME ARGS...
set -u; S=/srv/opentallas-scratch/claude/mu-dq-ctlmtl/src_fe8d9e2c1; W=/srv/opentallas-scratch/claude/mu-dq-ctlmtl/run1; N=$1; shift
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH; verilator --version > /srv/opentallas-scratch/claude/mu-dq-ctlmtl/run1/$N.out
cd $S && python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img results/rtl/qwen_layer_tput_1018/ctlm_prog/image --hard 1 --work /srv/opentallas-scratch/claude/mu-dq-ctlmtl/run1/prog_$N "$@" >> /srv/opentallas-scratch/claude/mu-dq-ctlmtl/run1/$N.out 2>&1
echo "exit $?" >> /srv/opentallas-scratch/claude/mu-dq-ctlmtl/run1/$N.out
