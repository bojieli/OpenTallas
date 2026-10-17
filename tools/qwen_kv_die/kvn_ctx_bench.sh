#!/bin/bash
# kvn_ctx_bench.sh OUT [MUT=0] [CH=12] [NTOK=2]: qkd_kvn_ctx_cal on the real KV link calendar sequencer + real KVN
# encode / receive check, against the link compiler's program calendar (tools/qwen_kv_die/kvn_ctx_golden.py).
# Prints one KVN_CTX line; exit 0 only on KVN_CTX PASS (mutants expect FAIL).  Run from the repository root.
set -u
O=$1; M=${2:-0}; CH=${3:-12}; NT=${4:-2}
mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/qwen_split/d2d_link_calendar.py --out "$O/cal" --txl 6 --phy 5 --profile program --txd-c 1,1,1,2 --txd-k 1,2,1,1 \
  --host-stages 0 --link-handoff results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json --pinreg \
  > "$O/calendar.log" 2>&1 || { echo "KVN_CTX FAIL calendar compile"; tail -3 "$O/calendar.log"; exit 1; }
python3 tools/qwen_kv_die/kvn_ctx_golden.py "$O/cal" "$O/gold" --ntok "$NT" --ch "$CH" || { echo "KVN_CTX FAIL golden"; exit 1; }
D=rtl/qwen_sys/d2d_static_20261015
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH -Wno-MODMISSING \
  --build-jobs 4 -I"$O/gold" -I"$D" --top-module tb_qkd_kvn_ctx_cal -GMUT=$M -GGOLD="\"$O/gold\"" --Mdir "$O/obj_m$M" \
  $D/qkd_kvn_ctx_cal.sv $D/qkd_d2d_cal_seq_pin.sv $D/ot_qwen_d2d_cal_seq.sv $D/ot_qwen_d2d_cal_seq_dies.sv $D/ot_qwen_d2d_dies.sv \
  rtl/test/qwen_split/tb_qkd_kvn_ctx_cal.sv > "$O/build_m$M.log" 2>&1 || { echo "KVN_CTX FAIL build"; grep -m5 -E '%Error' "$O/build_m$M.log"; exit 1; }
"$O/obj_m$M/Vtb_qkd_kvn_ctx_cal" > "$O/run_m$M.log" 2>&1
grep -E '^ERR' "$O/run_m$M.log" | head -5
line=$(grep -E '^KVN_CTX ' "$O/run_m$M.log" | tail -1)
echo "${line:-KVN_CTX FAIL no verdict line}"
case "$line" in "KVN_CTX PASS"*) exit 0;; *) exit 1;; esac
