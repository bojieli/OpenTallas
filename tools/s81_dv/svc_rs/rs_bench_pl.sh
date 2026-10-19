#!/usr/bin/env bash
# S81U-SVC6: dsdv_svc_rs exact bench, PROTECT-LIB build (replaces the --hierarchical build of rs_bench.sh, whose top-level
# verilate re-elaborated all 16 slices in V3Param: > 4 h single-thread at 66 GB without finishing).
#   step 1: dsdv_svc_rs and dsdv_svc_rs_entry are each built ONCE as a protect-lib (-GMUT/-GDIE_ID/-GST + the variant
#           defines baked in), in parallel;  step 2: the tb is built against the two wrappers only (-DRS_PL).
# Usage (repo root): DIE=0 ST=0 tools/s81_dv/svc_rs/rs_bench_pl.sh OUTDIR VECDIR VARIANT CASE ...   (variants as rs_bench.sh)
#   MAXCYC (tb cycle cap, default the tb's 400000) and PROG=1 (-DRS_PROG progress lines) select a separate top obj_<tag>;
#   the protect-libs are shared.
# SVCB (10-19): mut4 = p store wrong bank, mut5 = p store without the one-cycle prefetch (both: P.V errors);
#   PMEM_E (default 1) = the entry slices' p store (0 = dropped: the die kit for ST 0, entries 5 / 11 are not P.V owners);
#   mutpm = PMEM_E 0 at an ST whose owners include an entry slice (fault 23).
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; VEC=$2; V=$3; shift 3
SEEDS=${SEEDS:-"1 2"}; DIE=${DIE:-0}; ST=${ST:-0}; ENGDEF=${ENGDEF-SVCQ_ENG_FG3}; JOBS=${JOBS:-6}
source tools/s81_dv/svc_rs/rs_files.sh
DEF=(); MUTV=0
case "$V" in
  base) ;; mut1) MUTV=1;; mut2) MUTV=2;; mut3) MUTV=3;; mutgd) DEF=(-DRS_MUT_GD);; mutro) DEF=(-DRS_MUT_RO);;
  mut4) MUTV=4;; mut5) MUTV=5;; mut6) MUTV=6;; mut7) MUTV=7;; mutpm) PMEM_E=0;;
  *) echo "variant?" >&2; exit 2;;
esac
SRAM_MACRO=${SRAM_MACRO:-0}
[[ "$SRAM_MACRO" =~ ^[01]$ ]] || { echo "SRAM_MACRO must be 0 or 1" >&2; exit 2; }
PMEM_E=${PMEM_E:-1}
B=$O/${V}_d${DIE}s${ST}
[ "$PMEM_E" = 1 ] || [ "$V" = mutpm ] || B=${B}_pe0
[ "$SRAM_MACRO" = 1 ] && B=${B}_m1
# RS_XDEF (S81-CTRL-SVC 10-19): extra defines, e.g. "OT_SVC_LAND_SRAM" (landing in 12 SRAM macros; mut6 = no LVT)
XDEF=(); for x in ${RS_XDEF:-}; do XDEF+=(-D$x); B=${B}_${x,,}; done
TOPDEF=(); TAG=obj
[ -n "${MAXCYC:-}" ] && { TOPDEF+=(-GMAXCYC=$MAXCYC); TAG=${TAG}_m$MAXCYC; }
[ -n "${PROG:-}" ] && { TOPDEF+=(-DRS_PROG); TAG=${TAG}_prog; }
mkdir -p "$B"
COMMON=(-Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 2000 -fno-inline
        --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 -I$D -DRS_OBS ${ENGDEF:+-D$ENGDEF}
        "${RS_DEF[@]}" -DMUT=$MUTV "${DEF[@]}" "${XDEF[@]}")
lib() {  # $1 = module
  local L=$B/pl_$1 PM=1
  [ "$1" = dsdv_svc_rs_entry ] && PM=$PMEM_E
  [ -f "$L/lib$1_pl.a" ] && return 0
  "$VL" --cc --build -j "$JOBS" --protect-lib "$1_pl" --top-module "$1" -Mdir "$L" \
    -GMUT=$MUTV -GDIE_ID=$DIE -GST=$ST -GSRAM_MACRO=$SRAM_MACRO -GPMEM=$PM "${COMMON[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" > "$B/build_$1.log" 2>&1
}
if [ ! -x "$B/$TAG/Vtb_dsdv_svc_rs" ]; then
  lib dsdv_svc_rs & P1=$!; lib dsdv_svc_rs_entry & P2=$!
  wait $P1 || { tail -30 "$B/build_dsdv_svc_rs.log"; exit 1; }; wait $P2 || { tail -30 "$B/build_dsdv_svc_rs_entry.log"; exit 1; }
  "$VL" --binary --top-module tb_dsdv_svc_rs -Mdir "$B/$TAG" -GDIE=$DIE -GST=$ST -GSRAM_MACRO=$SRAM_MACRO -j "$JOBS" -DRS_PL "${TOPDEF[@]}" "${COMMON[@]}" \
    $B/pl_dsdv_svc_rs/dsdv_svc_rs_pl.sv $B/pl_dsdv_svc_rs_entry/dsdv_svc_rs_entry_pl.sv $D/test/tb_dsdv_svc_rs.sv \
    $B/pl_dsdv_svc_rs/libdsdv_svc_rs_pl.a $B/pl_dsdv_svc_rs_entry/libdsdv_svc_rs_entry_pl.a > "$B/build_$TAG.log" 2>&1 \
    || { tail -30 "$B/build_$TAG.log"; exit 1; }
fi
for C in "$@"; do
  for s in $SEEDS; do
    "$B/$TAG/Vtb_dsdv_svc_rs" +dir="$VEC/$C" +seed=$s > "$B/run_${C}_s${s}_$TAG.log" 2>&1 || true
    echo "$V d${DIE}s${ST} $C s$s ($TAG): $(grep -h '^SVCRS ' "$B/run_${C}_s${s}_$TAG.log" | tail -1)"
  done
done
