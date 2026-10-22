#!/bin/bash
set -euo pipefail
RUN=$1
MUT=${2:-0}
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p "$RUN"
python3 emit_balanced27.py qkd_kvs_attn_safe_pr32.v balanced27_model.json "$RUN/qkd_kvs_attn_safe_pr32b27.v" "$MUT" > "$RUN/emit.log"
python3 build_eq_bench.py qkd_kvs_attn_safe_control.v "$RUN/qkd_kvs_attn_safe_pr32b27.v" "$RUN" > "$RUN/bench_build.log"
gzip -dc models.v.gz > "$RUN/models.v"
verilator --version > "$RUN/build.log"
verilator --binary -j 8 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_pr --Mdir "$RUN/obj" -o vtb \
 "$RUN/tb_pr.sv" "$RUN/models.v" qkd_kvs_attn_safe_control.v "$RUN/qkd_kvs_attn_safe_pr32b27.v" >> "$RUN/build.log" 2>&1
set +e
"$RUN/obj/vtb" > "$RUN/sim.log" 2>&1
rc=$?
set -e
tail -n 5 "$RUN/sim.log"
echo "BALANCED27_EQ_MUT $MUT RC $rc"
exit "$rc"
