#!/bin/bash
# HKV-PROMPT6 (10-19): qkd_hr_core_prompt timing forks (gen_prompt_pd.py) equivalence benches.
#   prompt_pd_equiv.sh pass   OUT  -> HKV_PD_EQUIV PASS + HKV_CNT_LA PASS  => "HKV_PROMPT_PD PASS"
#   prompt_pd_equiv.sh mutant OUT  -> both benches built with their mutant define; each must FAIL => "HKV_PROMPT_PD FAIL mutant" lines
# Run from the repository root (Verilator 5.050, as the closure daemon).
set -u
MODE=${1:-pass}; OUT=${2:-/tmp/hkv_prompt_pd}; mkdir -p "$OUT"
M=physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
P=rtl/qwen_sys/host_cluster_20261017/prompt_pd
verilator --version
run() { # name defs top files...
  local n=$1 d=$2 top=$3; shift 3
  rm -rf "$OUT/$n"
  verilator --binary -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $d --top-module $top -Mdir "$OUT/$n" "$@" >"$OUT/$n.build.log" 2>&1 \
    || { tail -30 "$OUT/$n.build.log"; echo "BUILD_ERROR $n"; return 2; }
  "$OUT/$n/V$top" | tee "$OUT/$n.log"
}
PD="rtl/test/qwen_host/tb_hkv_prompt_pd_equiv.sv rtl/physical/ot_qkd_host_prompt_capture_pins.sv rtl/physical/ot_qfd_prompt_sram_capture.sv $P/qkd_host_prompt_capture_pins_pd.sv $P/ot_qfd_prompt_sram_capture_pd.sv $M"
CN="rtl/test/qwen_host/tb_hkv_cnt_la.sv $P/ot_hkv_cnt_la.sv"
if [ "$MODE" = pass ]; then
  run pd "" tb_hkv_prompt_pd_equiv $PD; run cn "" tb_hkv_cnt_la $CN
  if grep -q "HKV_PD_EQUIV PASS" "$OUT/pd.log" && grep -q "HKV_CNT_LA PASS" "$OUT/cn.log"; then echo "HKV_PROMPT_PD PASS"; else echo "HKV_PROMPT_PD FAIL"; exit 1; fi
else
  run pdm "-DQKD_HR_PD_MUTANT" tb_hkv_prompt_pd_equiv $PD; run cnm "-DOT_HKV_CNT_LA_MUTANT" tb_hkv_cnt_la $CN
  a=0; grep -q "HKV_PD_EQUIV FAIL" "$OUT/pdm.log" && { echo "HKV_PROMPT_PD FAIL mutant pd"; a=$((a+1)); }
  grep -q "HKV_CNT_LA FAIL" "$OUT/cnm.log" && { echo "HKV_PROMPT_PD FAIL mutant cnt"; a=$((a+1)); }
  [ $a = 2 ] && { echo "HKV_PROMPT_PD FAIL mutant 2/2"; exit 1; }
  echo "HKV_PROMPT_PD MUTANT_NOT_CAUGHT $a/2"; exit 0
fi
