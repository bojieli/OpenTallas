#!/bin/bash
# KV-ATTN 10-19 pin-registration equivalence bench (Verilator 5.050, actual Liberty models).
# usage: eq_bench.sh <run_dir> <MUT>   MUT 0 = pinreg.py as committed (PASS expected); 1/2 = pinreg.py mutants (FAIL expected)
set -euo pipefail
RUN=$1; MUT=${2:-0}
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p "$RUN"
D=rtl/qwen_sys/kv_bootage_20261019
T=tools/qwen_kv_die/attn_pinreg_1019
if [ "$MUT" = 0 ]; then PR=$D/qkd_kvs_attn_safe_pr.v; else PR=$RUN/pr_mut$MUT.v; python3 $T/pinreg.py $D/qkd_kvs_attn_safe_control.v $PR $RUN/pinreg_mut$MUT.json $MUT; fi
python3 $T/check_pinreg.py $PR | tee $RUN/check.log
python3 $T/build_eq_bench.py $D/qkd_kvs_attn_safe_control.v $PR $RUN
gzip -dc results/arch/kv_attn_safe_control_1019/models.v.gz > $RUN/models.v
verilator --version > $RUN/build.log
verilator --binary -j 8 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_pr --Mdir "$RUN/obj" -o vtb \
  $RUN/tb_pr.sv $RUN/models.v $D/qkd_kvs_attn_safe_control.v $PR >> $RUN/build.log 2>&1
set +e; "$RUN/obj/vtb" > $RUN/sim.log 2>&1; rc=$?; set -e
cat $RUN/sim.log | tail -3
echo "PR_EQ_RC $rc"
