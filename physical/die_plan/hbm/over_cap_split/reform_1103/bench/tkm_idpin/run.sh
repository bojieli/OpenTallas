#!/usr/bin/env bash
# DIE-HBM-61/SPLIT TKM tile RE-FORM chain proof (Verilator 5 hierarchical; fleet host).  run.sh REPO KIT_IDPIN_RTL KIT_TERM_RTL VECDIR OUT
#   REPO = checkout with rtl/hbm_accel/{generic/collective/tkm,cores_split/reform_1103/tkm_tile}, rtl/lib,
#          physical/asap7_memory_macros (or a dir holding ot_rst_relay.sv + the SRAM model as $LIBDIR)
#   VECDIR = tkm_split_vectors.py output.  Positive (MUTN 0 MUTP 0) must PASS every case; MUTN 1, MUTP 1, MUTP 2 FAIL.
set -u
R=$1; KI=$2; KT=$3; VEC=$4; O=$5; H=$(cd "$(dirname "$0")" && pwd); T=$H/../..
LIBDIR=${LIBDIR:-}; mkdir -p "$O"
RT=$R/rtl/hbm_accel/cores_split/reform_1103/tkm_tile; TK=$R/rtl/hbm_accel/generic/collective/tkm
RELAY=${LIBDIR:+$LIBDIR/ot_rst_relay.sv}; RELAY=${RELAY:-$R/rtl/lib/ot_rst_relay.sv}
SRAM=${LIBDIR:+$LIBDIR/ot_sram_1r1w_1024x256_m2_r2c2.v}; SRAM=${SRAM:-$R/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v}
python3 "$H/facewrap_tkm.py" --top ot_hgi_coll_tkm_tp192_htile_core --out "$O/htile__fs.sv" --clk-re '^tile_clk$' \
  "$RT/ot_hgi_coll_tkm_tp192_htile_core.sv" "$KI/ot_hgi_coll_tkm.sv" > "$O/htile_ports.json" || exit 1
SRC=("$H/tb_tkm_tile_split.sv" "$RT/ot_hgi_coll_tkm_static_pdh.sv" "$RT/ot_hgi_coll_tkm_tp192_htile_core.sv" "$RT/ot_hgi_coll_tkm_tp192_tile_core__split.sv"
     "$O/htile__fs.sv" "$KI/ot_hbm_face_reg.sv" "$KI/ot_hgi_coll_tkm.sv" "$KI/ot_hgi_coll_tkm_static.sv" "$KI/ot_hgi_coll_tkm_tp192_tile_core.sv"
     "$KI/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__fshell.sv" "$KI/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__wrap.sv"
     "$KT/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__fshell.sv" "$KT/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__wrap.sv"
     "$TK/ot_hgi_coll_tkm_buffer.sv" "$RELAY" "$SRAM")
sha256sum "${SRC[@]:1}" > "$O/sources.sha256"
CASES=${CASES:-full2048 part700}
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
build(){ # tag -G...
  local tag=$1; shift
  [ -x "$O/obj_$tag/Vtb" ] && return 0
  { "$V" --cc --exe --main --timing --hierarchical -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN       --top-module tb -Mdir "$O/obj_$tag" "$@" "$H/tkm_split_hier.vlt" "${SRC[@]}" &&
    make -C "$O/obj_$tag" -f Vtb_hier.mk -j1 hier_verilation && make -C "$O/obj_$tag" -f Vtb_hier.mk -j${JOBS:-8} hier_build; } > "$O/build_$tag.log" 2>&1     || { echo "BUILD FAIL $tag"; tail -8 "$O/build_$tag.log"; return 2; }
}
run(){ # tag case
  "$O/obj_$1/Vtb" +DIR="$VEC/$2" > "$O/${1}_$2.log" 2>&1
  echo "$1 $2: $(grep -m1 -E 'TKM_SPLIT (PASS|FAIL)' "$O/${1}_$2.log" || tail -1 "$O/${1}_$2.log")"
}
# each hierarchical build peaks at ~170 GB RSS (epyc2 earlyoom SIGTERMed pos/mutn 11-03 07:53/08:06): BUILD_PAR=2 builds two at a time, BUILD_PAR=1 serial (epyc4 450G cap OOM with 2 at 11-03 16:38)
if [ "${BUILD_PAR:-4}" -ge 4 ]; then build pos & build mutn -GMUTN=1 & build mutp1 -GMUTP=1 & build mutp2 -GMUTP=2 & wait
elif [ "${BUILD_PAR:-4}" -le 1 ]; then build pos; build mutn -GMUTN=1; build mutp1 -GMUTP=1; build mutp2 -GMUTP=2
else build pos & build mutn -GMUTN=1 & wait; build mutp1 -GMUTP=1 & build mutp2 -GMUTP=2 & wait; fi
for c in $CASES; do run pos $c & done
run mutn full2048 & run mutp1 full2048 & run mutp2 full2048 &
wait
