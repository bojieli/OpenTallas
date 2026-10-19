#!/usr/bin/env bash
# S81U-SVC: build + run the dsdv_svc_rs exact bench (16 slices: p4j entries 5 / 11 + 14, 2 x 8 grid, vs the dsfd_svc_c golden vectors
# of tools/v41_ckv_sel_attn_vectors.py).
# Usage (repo root): DIE=0 ST=0 tools/s81_dv/svc_rs/rs_bench.sh OUTDIR VECDIR VARIANT CASE ...
#   VARIANT: base | mut1 (window scale byte) | mut2 (ROWS half) | mut3 (q chunk) | mutgd (one slice's GO delay + 1)
#            | mutst (entry st_rg = its own controller live, children ignored; run with HSDROP=<sid>)
#            | mutro (the chain roots 07 / 09 flip a bit on their P.V return lane ro -> entry ri: tr_07_05 / tr_09_11)
#   ENGDEF (default SVCQ_ENG_FG3: the buildable engine latencies, same values), SEEDS (default "1 2")
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; VEC=$2; V=$3; shift 3
SEEDS=${SEEDS:-"1 2"}; DIE=${DIE:-0}; ST=${ST:-0}; ENGDEF=${ENGDEF-SVCQ_ENG_FG3}; JOBS=${JOBS:-6}
source tools/s81_dv/svc_rs/rs_files.sh
DEF=()
case "$V" in
  base) ;; mut1) DEF=(-DMUT=1);; mut2) DEF=(-DMUT=2);; mut3) DEF=(-DMUT=3);; mutgd) DEF=(-DRS_MUT_GD);; mutro) DEF=(-DRS_MUT_RO);; mutst) DEF=(-DRS_MUT_ST);;
  *) echo "variant?" >&2; exit 2;;
esac
B=$O/${V}_d${DIE}s${ST}
mkdir -p "$B"
if [ ! -x "$B/obj/Vtb_dsdv_svc_rs" ]; then
  # S81U-SVC4: HIERARCHICAL build -- dsdv_svc_rs_entry / dsdv_svc_rs are hier blocks (2 variants built once, not 16
  # flat copies; the flat 16-slice build ran > 75 min at 25 GB); the bench reads the slices through the RS_OBS ports
  "$VL" --binary --hierarchical --top-module tb_dsdv_svc_rs -Mdir "$B/obj" -GDIE=$DIE -GST=$ST -j "$JOBS" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
    --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 16 --unroll-limit 131072 \
    -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 \
    -I$D -DRS_OBS ${ENGDEF:+-D$ENGDEF} "${RS_DEF[@]}" "${DEF[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" $D/test/tb_dsdv_svc_rs.sv \
    > "$B/build.log" 2>&1 || { tail -30 "$B/build.log"; exit 1; }
fi
for C in "$@"; do
  for s in $SEEDS; do
    "$B/obj/Vtb_dsdv_svc_rs" +dir="$VEC/$C" +seed=$s ${HSDROP:++hsdrop=$HSDROP} > "$B/run_${C}_s$s.log" 2>&1 || true
    echo "$V d${DIE}s${ST} $C s$s: $(grep -h '^SVCRS_ST ' "$B/run_${C}_s$s.log" | tail -1) | $(grep -h '^SVCRS ' "$B/run_${C}_s$s.log" | tail -1)"
  done
done
