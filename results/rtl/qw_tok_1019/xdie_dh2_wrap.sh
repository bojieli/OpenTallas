#!/bin/bash
# QW-TOK 10-19: of-record compute die dv2f18dh2 (src 0d4c9808f) D2D token pieces, Verilator 5.050.
#  (a) 1-user paired compute<->KV co-sim on the dv2f18dh2 netlisted seam with the image TXDPs the GENs bind (xdie_txdp_job.sh)
#  (b) 4-user compute D2D endpoint (qfd_native59_dv_service NU4) bench on the same source
set -u
W=/srv/opentallas-scratch/claude/qw-tok/xdie_dh2
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; export PATH=$(dirname $VERILATOR):$PATH
verilator --version
( bash $W/src/rtl/test/qwen_split/xdie_txdp_job.sh $W $W/die_dv2f18dh2.v > $W/xdie_txdp.out 2>&1 ) &
( bash $W/src/rtl/test/qwen_split/run_native59_dv_mu_bench.sh $W/n59mu > $W/n59mu.out 2>&1; echo "n59mu rc=$?" >> $W/n59mu.out ) &
wait
tail -20 $W/xdie_txdp.out; tail -12 $W/n59mu.out; echo QWTOK_XDIE_DH2_DONE
