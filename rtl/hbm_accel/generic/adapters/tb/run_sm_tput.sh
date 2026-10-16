#!/usr/bin/env bash
# hgi-1010/g: SM.MATVEC throughput bench (tb_hgi_sm_tput).  usage: run_sm_tput.sh <qwen|ds> <outdir> [MUT_ROW|MUT_EARLY] [+LAT=n +BWX10=n]
# ds needs META=<hgi-e2e export meta.json>.  ONLY=<n>: first n records (smoke).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
V=$1; OUT=$(realpath -m "$2"); MUT=${3:-}; shift 3 || shift $#
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
[ -f "$OUT/vec/tput_rec.mem" ] || python3 tools/hgi_adapters/sm_tput_bench.py $V ${META:+--meta $META} ${ONLY:+--only $ONLY} --out "$OUT/vec" > "$OUT/gen.log"
SRC="physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/generic/vm/ot_hgi_vm_lanearb.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_wrd.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_wblk.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hbm_accel/generic/adapters/ot_hgi_sm_record.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv
     rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
     $(python3 -c "import sys; sys.path.insert(0,'tools'); import dshbm_sm_pq_seq as Q; print(' '.join(s for s in Q.SRC + Q.SMH_SRC if 'rtl/test/' not in s))")"
D="${XDEF:-}"; [ -n "$MUT" ] && D="$D -D$MUT"
O="$OUT/obj${MUT:+_$MUT}"
"$VL" --binary --timing -O3 -CFLAGS -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN $D \
  --top-module tb_hgi_sm_tput -I"$OUT/vec" -Mdir "$O" $SRC rtl/hbm_accel/generic/adapters/tb/tb_hgi_sm_tput.sv -j ${J:-16} \
  > "$OUT/build${MUT:+_$MUT}.log" 2>&1 || { tail -30 "$OUT/build${MUT:+_$MUT}.log"; exit 2; }
"$O/Vtb_hgi_sm_tput" +DIR="$OUT/vec" "$@" > "$OUT/run${MUT:+_$MUT}${TAG:+_$TAG}.log" 2>&1 || true
tail -4 "$OUT/run${MUT:+_$MUT}${TAG:+_$TAG}.log"
