#!/bin/bash
# sys-takeover 2026-10-09: KV write ECC at the die's real write timing (tb_qfd_kvw2_path: STREAM4 CDC -> pcport KVW 2
# -> behavioural HBM 288 b -> ot_qfd_kv_landing_ecc).  pos: PASS_ALL.  neg: MUT 4 (wrong check column), MUT 5 (side-band
# dropped), LATE (data two edges after the column) and KVWM 1 (the KVW 1 port at this timing) must all FAIL.
#   kvw2_path_bench.sh pos|neg OUT
set -uo pipefail
mode=$1; W=$2; mkdir -p "$W"
S=(rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv
   rtl/qwen_sys/q5_20261009/ot_qfd_kv_landing_ecc.sv rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv rtl/test/emb_hbm/tb_qfd_kvw2_path.sv)
run() {   # tag, -P overrides...
  local t=$1; shift
  iverilog -g2012 "$@" -s tb_qfd_kvw2_path -o "$W/sim_$t" "${S[@]}" >"$W/build_$t.log" 2>&1 || { tail -5 "$W/build_$t.log"; echo KVW2_BENCH_ERROR; exit 2; }
  timeout 1200 vvp -n "$W/sim_$t" >"$W/run_$t.log" 2>&1
}
if [[ $mode == pos ]]; then
  run base; grep -E "^PASS|FATAL" "$W/run_base.log"
  grep -q '^PASS_ALL' "$W/run_base.log" && ! grep -q FATAL "$W/run_base.log" && { echo KVW2_PATH_PASS; exit 0; }
  echo KVW2_PATH_FAIL; exit 1
fi
n=0
for v in "m4 -Ptb_qfd_kvw2_path.MUT=4" "m5 -Ptb_qfd_kvw2_path.MUT=5" "late -Ptb_qfd_kvw2_path.LATE=1" "kvw1 -Ptb_qfd_kvw2_path.KVWM=1"; do
  set -- $v; run "$@"; echo "$1: $(grep -m1 -E 'FATAL|PASS_ALL' "$W/run_$1.log")"; grep -q FATAL "$W/run_$1.log" && n=$((n+1))
done
[[ $n == 4 ]] && { echo "KVW2_PATH_NEG_DETECTED 4/4"; exit 1; }
echo "KVW2_PATH_NEG_MISSED $n/4"; exit 0
