#!/usr/bin/env bash
# hgi-1010/g: ATT unit THROUGHPUT bench (tb_hgi_att_tput).  usage: run_att_tput.sh <outdir> [MUTANT define]
#   env: CASES (att_tput_vectors.py --cases), KLAT (HBM lane latency; empty = random-order stalling model),
#        DEFS (extra -D, e.g. "-DATT_D=128 -DATT_PIPE=1"), NPAR (processes, case c on process c mod NPAR)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_att_tput}"); MUT=${2:-}
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
python3 tools/hgi_adapters/att_tput_vectors.py --out "$OUT/vec" --cases "${CASES:-qwen_T512,qwen_T1024,ds_L0,ds_L20,ring_wrap}" > "$OUT/gen.log"
SRC="rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv
  rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv rtl/hbm_accel/generic/peers/ot_hgi_att_unit.sv
  rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
D="${DEFS:-}"; [ -n "$MUT" ] && D="$D -D$MUT"
if [ ! -x "$OUT/obj/Vtb_hgi_att_tput" ]; then
"$VL" --binary --timing -O3 -CFLAGS -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN $D \
  --top-module tb_hgi_att_tput -I"$OUT/vec" -Mdir "$OUT/obj" $SRC rtl/hbm_accel/generic/adapters/tb/tb_hgi_att_tput.sv \
  -j ${J:-16} > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 2; }
fi
NPAR=${NPAR:-1}; K=""; [ -n "${KLAT:-}" ] && K="+KLAT=$KLAT"
for k in $(seq 0 $((NPAR - 1))); do
  "$OUT/obj/Vtb_hgi_att_tput" +DIR="$OUT/vec" +FIRST=$k +STEP=$NPAR $K > "$OUT/run.$k.log" &
done
wait
cat "$OUT"/run.*.log > "$OUT/run.log"
if grep -q "FAIL" "$OUT/run.log" || [ $(grep -c "HGI_ATT_TPUT PASS" "$OUT/run.log") -ne $NPAR ]; then echo "HGI_ATT_TPUT FAIL"; else echo "HGI_ATT_TPUT PASS ($NPAR shards)"; fi
