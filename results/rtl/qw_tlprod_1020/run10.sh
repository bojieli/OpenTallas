#!/bin/bash
# QW-TLPROD 10-20 fleet run: regenerate the bounded netlist (generic -> construct -> native census -> depth) with the
# TABLE_REL cal_mu, install it as rtl/qwen_dv/lp9d_np, then the V5.050 bench and the calr_port unit regression.
set -uo pipefail
R=$(cd "$(dirname "$0")/.." && pwd)
# TABLE_REL unit bench (NU 4: user 0 descriptor + fillers explicit range, 144 loads)
rm -f $R/calr_rel.log
for c in "0 calr10 m0" "35 calr10 m35" "0 calr10n none" "0 calr10a abs1"; do set -- $c
  cd $R/src && PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH bash rtl/test/qwen_dv/calr_rel/run_calr_rel.sh $R/calr_rel_$3 $1 $R/src/$2 > $R/calr_rel_$3.log 2>&1; echo "CALR_REL_$3 rc=$?" >> $R/calr_rel.log; grep -E "CALR_REL_(SUMMARY|PASS|FAIL|BAD)" $R/calr_rel_$3.log | head -4 >> $R/calr_rel.log; done
echo RUN10_UNIT_DONE
docker run --rm -u $(id -u):$(id -g) -v $R:/work -w /work/src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; bash chain9.sh' > $R/chain10.log 2>&1; echo "CHAIN_RC $?" >> $R/chain10.log
docker run --rm -u $(id -u):$(id -g) -v $R:/work -w /work/src openroad/orfs:latest bash -lc 'bash depth7.sh' > $R/depth10.log 2>&1; echo "DEPTH_RC $?" >> $R/depth10.log
mkdir -p $R/src/rtl/qwen_dv/lp9d_np && cp $R/generic7c/qfd_tt_ctlm_dv_np_lp.sv $R/generic7c/qfd_tt_ctlm_dv_np_helpers.sv $R/src/rtl/qwen_dv/lp9d_np/
cd $R/src && bash bench10.sh > $R/bench10.log 2>&1; echo "BENCH_RC $?" >> $R/bench10.log
cd $R/src && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
rm -f $R/calr_port.log
for m in 0 34 2; do bash rtl/test/qwen_dv/calr_port/run_calr_port.sh $R/calr_port_m$m $m > $R/calr_port_m$m.log 2>&1; echo "CALR_PORT_M$m rc=$?" >> $R/calr_port.log; tail -3 $R/calr_port_m$m.log >> $R/calr_port.log; done
echo RUN10_BENCH_DONE
