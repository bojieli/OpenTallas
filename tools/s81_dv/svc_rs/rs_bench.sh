#!/usr/bin/env bash
# S81U-SVC: build + run the dsdv_svc_rs exact bench (16 slices: root + 15, 2 x 8 grid, vs the dsfd_svc_c golden vectors
# of tools/v41_ckv_sel_attn_vectors.py).
# Usage (repo root): DIE=0 ST=0 tools/s81_dv/svc_rs/rs_bench.sh OUTDIR VECDIR VARIANT CASE ...
#   VARIANT: base | mut1 (window scale byte) | mut2 (ROWS half) | mut3 (q chunk) | mutgd (one slice's GO delay + 1)
#   ENGDEF (default SVCQ_ENG_FG3: the buildable engine latencies, same values), SEEDS (default "1 2")
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; VEC=$2; V=$3; shift 3
SEEDS=${SEEDS:-"1 2"}; DIE=${DIE:-0}; ST=${ST:-0}; ENGDEF=${ENGDEF-SVCQ_ENG_FG3}; JOBS=${JOBS:-16}
source tools/s81_dv/svc_rs/rs_files.sh
DEF=()
case "$V" in
  base) ;; mut1) DEF=(-DMUT=1);; mut2) DEF=(-DMUT=2);; mut3) DEF=(-DMUT=3);; mutgd) DEF=(-DRS_MUT_GD);;
  *) echo "variant?" >&2; exit 2;;
esac
B=$O/${V}_d${DIE}s${ST}
mkdir -p "$B"
if [ ! -x "$B/obj/Vtb_dsdv_svc_rs" ]; then
  "$VL" --binary --top-module tb_dsdv_svc_rs -Mdir "$B/obj" -GDIE=$DIE -GST=$ST -j "$JOBS" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
    --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 1 --unroll-limit 131072 \
    -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 \
    -I$D ${ENGDEF:+-D$ENGDEF} "${RS_DEF[@]}" "${DEF[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" $D/test/tb_dsdv_svc_rs.sv \
    > "$B/build.log" 2>&1 || { tail -30 "$B/build.log"; exit 1; }
fi
for C in "$@"; do
  for s in $SEEDS; do
    "$B/obj/Vtb_dsdv_svc_rs" +dir="$VEC/$C" +seed=$s > "$B/run_${C}_s$s.log" 2>&1 || true
    echo "$V d${DIE}s${ST} $C s$s: $(grep -h '^SVCRS ' "$B/run_${C}_s$s.log" | tail -1)"
  done
done
