#!/bin/bash
# Exact existing staged head versus actual87-child inner+external T1/S1.
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1")
mkdir -p "$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
sources=(
 rtl/test/qwen_split/tb_qkh_head_inner_t2.sv
 rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4_s2.sv
 rtl/qwen_sys/split_20261014/qkh_head_stages.sv
 rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv
 rtl/qwen_sys/split_20261014/ot_qkh_head_native_r3.sv
 rtl/qwen_sys/split_20261014/ot_qkh_head_native.sv
 rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv
 rtl/hdc/nearhbm/ot_qkh_subtiles.sv
 rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv
 rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv
 rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
)
python3 - "$out" "${sources[@]}" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);files=sys.argv[2:]+['rtl/test/qwen_split/run_qkh_head_inner_t2.sh','tools/qwen_kv_die/head_inner_t2.py']
(p/'source_manifest.json').write_text(json.dumps({'scope':'Component87-child inner+externalT1/S1 versus existing staged head; same phase leaf clocks only; no physical timing/parent qualification','files_sha256':{n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in files}},indent=2)+'\n')
PY
"$v" --binary --timing -j "${JOBS:-2}" -O1 --x-assign 0 --x-initial 0  --output-split 20000 --output-split-cfuncs 5000 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD  +define+KVD_Q_FP32=1 --top-module tb_qkh_head_inner_t2 --Mdir "$out/obj" -o tb "${sources[@]}" > "$out/build.log" 2>&1
"$out/obj/tb" > "$out/normal.log" 2>&1
grep -q 'HEAD_NATIVE_PASS checks=3515' "$out/normal.log"
for mode in 1 2; do
 set +e
 "$out/obj/tb" +negative=$mode > "$out/negative$mode.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$out/negative$mode.exit"
 if [ "$rc" = 0 ] || ! grep -q 'HEAD_NATIVE_FAIL checks=3515 errors=' "$out/negative$mode.log"; then
  cat "$out/negative$mode.log"
  exit 1
 fi
done
cat "$out/normal.log"
echo 'HEAD_INNER_T2_GATE PASS real87-child composition + original3515 checks + T1/S1 negative controls rejected'
