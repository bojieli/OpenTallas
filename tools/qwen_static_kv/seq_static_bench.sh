#!/bin/bash
# seq_static_bench.sh OUT [MUT=0] [NL=36] [ARR_MUT=0]: qkd_seq_static vs the legacy qkd_seq on link-compiler-slotted layer traffic
# (tb_seq_static).  One SEQ_STATIC line; exit 0 only on PASS (mutants expect FAIL).  Run from the repository root.
set -u
O=$1; M=${2:-0}; NL=${3:-36}; AM=${4:-0}
mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/qwen_split/d2d_link_calendar.py --out "$O/cal" --txl 6 --phy 5 --profile program --txd-c 1,1,1,2 --txd-k 1,2,1,1 \
  --host-stages 0 --link-handoff results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json --pinreg \
  > "$O/calendar.log" 2>&1 || { echo "SEQ_STATIC FAIL calendar compile"; exit 1; }
rm -rf "$O/lp"; python3 tools/qwen_static_kv/layer_roots_from_link.py "$O/cal" "$O/lp" > "$O/roots.log" 2>&1 || { echo "SEQ_STATIC FAIL roots"; exit 1; }
mkdir -p "$O/g"; python3 tools/qwen_static_kv/seq_static_golden.py "$O/cal" "$O/lp/layer_roots.json" "$O/g/seq_gold.svh" || { echo "SEQ_STATIC FAIL golden"; exit 1; }
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 4 \
  -I"$O/g" --top-module tb_seq_static -GMUT=$M -GNL=$NL -GARR_MUT=$AM --Mdir "$O/obj_m$M" \
  rtl/lib/ot_rst_relay.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv \
  rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv rtl/physical/ot_qwen_kv_centre_slots.sv rtl/physical/ot_qwen_kv_seq_tp8.sv \
  rtl/qwen_sys/static_kv_20261014/qkd_seq_static.sv rtl/test/qwen_static_kv/tb_seq_static.sv > "$O/build_m$M.log" 2>&1 \
  || { echo "SEQ_STATIC FAIL build"; grep -m6 '%Error' "$O/build_m$M.log"; exit 1; }
"$O/obj_m$M/Vtb_seq_static" > "$O/run_m$M.log" 2>&1
grep -E '^ERR' "$O/run_m$M.log" | head -6
line=$(grep -E '^SEQ_STATIC ' "$O/run_m$M.log" | tail -1)
echo "${line:-SEQ_STATIC FAIL no verdict line}"
case "$line" in "SEQ_STATIC PASS"*) exit 0;; *) exit 1;; esac
