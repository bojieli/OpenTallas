#!/bin/bash
# seq_static_s_bench.sh OUT [MUT=0] [NL=36]: qkd_seq_static_s (no legacy landing faces kvn_<q>_d / kvn_<q>_cr / mf_<q>,
# RTL-BUILD-KV/SEQ P3) in LOCKSTEP against qkd_seq_static_p (always-available landing credit, mf 0) on link-compiler-slotted
# layer traffic with the actual attention programme RTL (tb_seq_static_s).  One SEQ_S line; exit 0 only on PASS (mutants
# expect FAIL).  Run from the repository root (on the fleet via ot-run).
set -u
O=$1; M=${2:-0}; NL=${3:-36}
mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/qwen_split/d2d_link_calendar.py --out "$O/cal" --txl 6 --phy 5 --profile program --txd-c 1,1,1,2 --txd-k 1,2,1,1 \
  --host-stages 0 --link-handoff results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json --pinreg \
  > "$O/calendar.log" 2>&1 || { echo "SEQ_S FAIL calendar compile"; exit 1; }
rm -rf "$O/lp"; python3 tools/qwen_static_kv/layer_roots_from_link.py "$O/cal" "$O/lp" > "$O/roots.log" 2>&1 || { echo "SEQ_S FAIL roots"; exit 1; }
mkdir -p "$O/g"; python3 tools/qwen_static_kv/seq_static_golden.py "$O/cal" "$O/lp/layer_roots.json" "$O/g/seq_gold.svh" || { echo "SEQ_S FAIL golden"; exit 1; }
S=rtl/qwen_sys/split_20261014
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 4 \
  -I"$O/g" --top-module tb_seq_static_s -GMUT=$M -GNL=$NL --Mdir "$O/obj_m$M" \
  rtl/lib/ot_rst_relay.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv \
  rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv \
  rtl/physical/ot_qwen_kv_centre_slots.sv rtl/physical/ot_qwen_kv_seq_tp8.sv \
  $S/qkd_native59_descriptor_producer.sv $S/qkd_native59_command_guard.sv $S/qkd_native_attention_record.sv \
  $S/qkd_native_attention_static_ctl.sv $S/qkd_native_attention_programme.sv \
  rtl/qwen_sys/static_kv_20261014/qkd_seq_static_prg.sv rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv \
  rtl/test/qwen_static_kv/tb_seq_static_s.sv > "$O/build_m$M.log" 2>&1 \
  || { echo "SEQ_S FAIL build"; grep -m6 '%Error' "$O/build_m$M.log"; exit 1; }
"$O/obj_m$M/Vtb_seq_static_s" > "$O/run_m$M.log" 2>&1
grep -E '^(ERR|DIE_CR0)' "$O/run_m$M.log" | head -8
line=$(grep -E '^SEQ_S ' "$O/run_m$M.log" | tail -1)
echo "${line:-SEQ_S FAIL no verdict line}"
case "$line" in "SEQ_S PASS"*) exit 0;; *) exit 1;; esac
