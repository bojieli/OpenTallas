#!/bin/bash
# sys-takeover 2026-10-09: qfd_hbm_ecc_provider bench (pcport KVW=1 -> behavioural HBM 288-b -> ot_qfd_kv_landing_ecc).
#   hbm_ecc_provider_bench.sh pos|neg OUT   (neg: MUT 4 wrong check column and MUT 5 side-band dropped must both FAIL)
set -uo pipefail
mode=$1; W=$2; mkdir -p "$W"
S=(rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv
   rtl/qwen_sys/q5_20261009/ot_qfd_kv_landing_ecc.sv rtl/test/emb_hbm/tb_qfd_hbm_ecc_provider.sv)
run() {
  iverilog -g2012 -P tb_qfd_hbm_ecc_provider.MUT=$1 -s tb_qfd_hbm_ecc_provider -o "$W/sim$1" "${S[@]}" >"$W/build$1.log" 2>&1 \
    || { tail -5 "$W/build$1.log"; echo HECC_BENCH_ERROR; exit 2; }
  vvp -n "$W/sim$1" >"$W/run$1.log" 2>&1
}
if [[ $mode == pos ]]; then
  run 0; grep -E "^PASS|FATAL" "$W/run0.log"
  grep -q '^PASS_ALL' "$W/run0.log" && ! grep -q FATAL "$W/run0.log" && { echo HBM_ECC_PROVIDER_PASS; exit 0; }
  echo HBM_ECC_PROVIDER_FAIL; exit 1
fi
n=0
for m in 4 5; do run $m; grep -m1 -E "FATAL|PASS_ALL" "$W/run$m.log"; grep -q FATAL "$W/run$m.log" && n=$((n+1)); done
[[ $n == 2 ]] && { echo "HBM_ECC_PROVIDER_NEG_DETECTED 2/2"; exit 1; }
echo "HBM_ECC_PROVIDER_NEG_MISSED $n/2"; exit 0
