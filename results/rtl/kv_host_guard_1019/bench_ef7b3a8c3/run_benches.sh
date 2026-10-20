#!/bin/bash
# KV-HOST/GUARD 10-19: MU1+SRAM guard benches at Verilator 5.050 on the fleet (source = git archive of the branch commit)
set -u
B=$(cd "$(dirname "$0")" && pwd); cd "$B/src"; O="$B/out"; rm -rf "$O"; mkdir -p "$O"
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
export PATH=$(dirname "$VERILATOR"):$PATH
echo "src $(cat SRC_COMMIT) $($VERILATOR --version)" | tee "$O/summary.txt"
for c in lint_guard_mu tb_mu_hroot_e2e ep1 ep2; do
  bash rtl/test/mu_qwen_1018/run_mu_hroot.sh . "$O/mu" $c >> "$O/summary.txt" 2>&1; echo "rc[$c]=$?" >> "$O/summary.txt"
done
RUN="$O/lint_sram"; CMD=$(cat "$B/lint_cmd.txt"); CMD=${CMD//\{RUN\}/$RUN}
bash -c "$CMD" > "$O/lint_sram.log" 2>&1; echo "rc[lint_sram]=$? $(tail -1 $O/lint_sram.log)" >> "$O/summary.txt"
for m in 0 1 2 3; do
  bash results/rtl/kv_guard_fifo_sram_1019/run_verilator.sh "$O/fifo_m$m" $m > "$O/fifo_m$m.out" 2>&1; echo "rc[fifo_m$m]=$? $(grep -h -E 'PASS cycles|%Fatal|GUARD_FIFO' $O/fifo_m$m.out | head -2 | tr '\n' ' ')" >> "$O/summary.txt"
done
rm -rf "$O"/mu/src_* "$O"/fifo_m*/obj
cat "$O/summary.txt"
