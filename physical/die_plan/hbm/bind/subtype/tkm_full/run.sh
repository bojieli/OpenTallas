#!/usr/bin/env bash
# BIND-SUBTYPE-2 11-11 (DO_NOT_COUNT): full-shape TKM exactness bench of the bound root pieces (tb_tkm_root_full.sv).
#   run.sh SRC ROOTKIT_RTL ROOT_FORM.sv MUTN_ROOT.sv OUT [TAG]
#   SRC          source tree of the bind (kw41/src_hbmf4_m3): p19glue, __splitc, htile, generic tkm, tkm_split_vectors.py
#   ROOTKIT_RTL  root kit rtl dir (ot_hgi_coll_tkm_m_tp192__root__fshell.sv / __wrap.sv / ot_hbm_face_reg.sv / ot_hbm_face_rst_relay.sv)
#   ROOT_FORM    ot_hgi_coll_tkm_tp192_root_core.sv of the plan's form (positive);  MUTN_ROOT = 32-element root (negative)
#   TAG          pos | mutn | mutu (one build per ot-run job); default: all three, serial.
# pos runs full2048 + part700 (must PASS); mutn / mutu run full2048 (must FAIL).
set -u
S=$1; RK=$2; RF=$3; RM=$4; O=$5; ONLY=${6:-}; H=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$O"; touch "$O/DO_NOT_COUNT"
B=$S/physical/die_plan/hbm/over_cap_split/reform_1103/bench/tkm_idpin
P19=$S/results/die_hbm_1104/reform_a/part19
TT=$S/rtl/hbm_accel/cores_split/reform_1103/tkm_tile
TK=$S/rtl/hbm_accel/generic/collective/tkm
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
[ -d "$O/vec" ] || python3 -I "$B/tkm_split_vectors.py" --out "$O/vec" --tools "$S/tools" --kmax 2048 > "$O/vectors.log" 2>&1 || { echo VEC_FAIL; exit 2; }
# del_flit: the root core reads 2116 of the master's 2180 bits (rest_wrap); the bench drives bit j from full bit i
grep -o 'assign del_flit__full\[[0-9]*\] = del_flit\[[0-9]*\];' "$RF" | sed -E 's/assign del_flit__full\[([0-9]+)\] = del_flit\[([0-9]+)\];/ assign dflit[\2]=flits[\1];/' > "$O/tb_dflit_map.svh"
[ "$(wc -l < "$O/tb_dflit_map.svh")" = 2116 ] || { echo DFLIT_MAP_FAIL; exit 2; }
# htile in kit face-shell form (facewrap_tkm.py = the kit face_shell.py form), and __splitc instantiating it
[ -f "$O/htile__fs.sv" ] || python3 -I "$B/facewrap_tkm.py" --top ot_hgi_coll_tkm_tp192_htile_core --out "$O/htile__fs.sv" --clk-re '^tile_clk$' \
  "$TT/ot_hgi_coll_tkm_tp192_htile_core.sv" "$TK/ot_hgi_coll_tkm.sv" > "$O/htile_ports.json" || { echo FACEWRAP_FAIL; exit 2; }
# hier-block module name without '__' (Verilator encodes it as ___05F and the top then misses the wrapper module)
sed 's/\bot_hgi_coll_tkm_tp192_htile_core__fs\b/ot_hgi_coll_tkm_tp192_htilefs/' "$O/htile__fs.sv" > "$O/htilefs.sv"
[ "$(grep -c '^module ot_hgi_coll_tkm_tp192_htilefs\b' "$O/htilefs.sv")" = 1 ] || { echo HTILEFS_FAIL; exit 2; }
sed -E 's/^(\s*)ot_hgi_coll_tkm_tp192_htile_core (u_h[ab])/\1ot_hgi_coll_tkm_tp192_htilefs \2/' \
  "$S/rtl/hbm_accel/cores_split/reform_1104a/tkm_tile/ot_hgi_coll_tkm_tp192_tile_core__splitc.sv" > "$O/splitc__fs.sv"
[ "$(grep -c 'htilefs u_h' "$O/splitc__fs.sv")" = 2 ] || { echo SPLITC_FS_FAIL; exit 2; }
# Blocks built as separate --lib-create DPI libraries (the half tile once, the root core per form), top built against
# their wrappers only.  History: plain build OOM at 96 GB (root in top, 11-11 10:58 UTC); Verilator --hierarchical
# still parsed and elaborated the block sources in the top pass (tb.g_t[*]...u_tile paths, 38-45 GB within minutes,
# killed by earlyoom/caps 11-11 13:4x-14:00 UTC), and --hierarchical runs the top pass itself, so the args cannot be cut.
COMMON=("$H/tb_tkm_root_full.sv" "$RK/ot_hgi_coll_tkm_m_tp192__root__fshell.sv" "$RK/ot_hgi_coll_tkm_m_tp192__root__wrap.sv"
  "$RK/ot_hbm_face_reg.sv" "$RK/ot_hbm_face_rst_relay.sv"
  "$P19/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__p19glue.sv" "$P19/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__p19glue.sv"
  "$O/splitc__fs.sv" "$S/rtl/lib/ot_rst_relay.sv")
BLK=("$O/htilefs.sv" "$TT/ot_hgi_coll_tkm_tp192_htile_core.sv" "$TK/ot_hgi_coll_tkm.sv" "$RK/ot_hbm_face_reg.sv" "$RK/ot_hbm_face_rst_relay.sv"
  "$S/rtl/lib/ot_rst_relay.sv" "$S/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v")
sha256sum "${COMMON[@]}" "${BLK[@]}" "$RF" "$RM" "$O/tb_dflit_map.svh" "$B/tkm_split_vectors.py" > "$O/sources.sha256"
VW=(-O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN)
lib(){ # mdir name top files...
  local md=$1 nm=$2 top=$3; shift 3
  [ -f "$md/lib$nm.a" ] && [ -f "$md/$nm.sv" ] && return 0
  "$V" --cc --no-timing --lib-create "$nm" --top-module "$top" "${VW[@]}" -Mdir "$md" --build -j "${JOBS:-8}" "$@"
}
build(){ # tag rootfile -G...
  local tag=$1 rf=$2; shift 2
  [ -x "$O/obj_$tag/Vtb" ] && return 0
  { lib "$O/lib_htile" htilefs ot_hgi_coll_tkm_tp192_htilefs "${BLK[@]}" &&
    lib "$O/lib_root_$tag" rootcore ot_hgi_coll_tkm_tp192_root_core "$rf" "$S/rtl/lib/ot_rst_relay.sv" "$RK/ot_hbm_face_reg.sv" "$RK/ot_hbm_face_rst_relay.sv" \
      "$S/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" &&
    "$V" --cc --exe --main --timing --build -j "${JOBS:-8}" "${VW[@]}" --top-module tb -I"$O" -Mdir "$O/obj_$tag" "$@" "${COMMON[@]}" \
      "$O/lib_htile/htilefs.sv" "$O/lib_root_$tag/rootcore.sv" "$O/lib_htile/libhtilefs.a" "$O/lib_root_$tag/librootcore.a"; } \
    > "$O/build_$tag.log" 2>&1 || { echo "BUILD FAIL $tag"; tail -8 "$O/build_$tag.log"; return 2; }
}
run(){ "$O/obj_$1/Vtb" +DIR="$O/vec/$2" > "$O/${1}_$2.log" 2>&1; echo "$1 $2: $(grep -m1 -E 'TKM_FULL (PASS|FAIL)' "$O/${1}_$2.log" || tail -1 "$O/${1}_$2.log")"; }
one(){ case $1 in
  lint) "$V" --lint-only --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN --top-module tb -I"$O" \
          "${COMMON[@]}" "${BLK[@]}" "$RF" > "$O/lint.log" 2>&1; echo "LINT_RC $?"; grep -m5 '%Error' "$O/lint.log";;
  pos) build pos "$RF" || return 2; run pos full2048; run pos part700;;
  mutn) build mutn "$RM" || return 2; run mutn full2048;;
  mutu) build mutu "$RF" -GMUTU=1 || return 2; run mutu full2048;;
 esac; }
if [ -n "$ONLY" ]; then one "$ONLY"; else one pos; one mutn; one mutu; fi
