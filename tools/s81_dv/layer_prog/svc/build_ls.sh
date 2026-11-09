#!/usr/bin/env bash
# S81-SVC-5: build the lock-step bench at H = $2 (16 | 8) into $1 (protect-lib slices + tb_svc_lockstep).
# Run from the repo root.  H8 = -DOT_SVC_H8 -DOT_SVC_H8_REUSE_RT2 (R5 RT2 form); both: closing ALLQ engine profile.
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$(realpath -m "$1"); HH=$2; JOBS=${JOBS:-8}; OPT=${LS_CXX_OPT:--O0}
source tools/s81_dv/svc_rs/rs_files.sh
RS_DEF+=(-DOT_SVC_ALLQ -DOT_ATTN_HCORE -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED)
RS_SRC+=(rtl/hdc/v41x/ot_s81c_attn_hcore.sv rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv)
[ "$HH" = 8 ] && RS_DEF+=(-DOT_SVC_H8 -DOT_SVC_H8_REUSE_RT2)
mkdir -p "$O"; "$VL" --version > "$O/verilator.version"
COMMON=(-Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 2000 -fno-inline
        --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS $OPT -I$D -DRS_OBS
        "${RS_DEF[@]}" -DMUT=0 ${MUTDEF:+-D$MUTDEF})
lib() {
  local L=$O/pl_$1
  [ -f "$L/lib$1_pl.a" ] && return 0
  /usr/bin/time -v "$VL" --cc --build -j "$JOBS" --protect-lib "$1_pl" --top-module "$1" -Mdir "$L" \
    -GMUT=0 -GDIE_ID=0 -GST=0 "${COMMON[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" > "$O/build_$1.log" 2>&1
}
TB=tools/s81_dv/layer_prog/svc/tb_svc_lockstep.sv
echo "build start $(date) H=$HH defs: ${RS_DEF[*]}"
lib dsdv_svc_rs & P1=$!; lib dsdv_svc_rs_entry & P2=$!
wait $P1 || { tail -30 "$O/build_dsdv_svc_rs.log"; exit 1; }; wait $P2 || { tail -30 "$O/build_dsdv_svc_rs_entry.log"; exit 1; }
/usr/bin/time -v "$VL" --binary --top-module tb_svc_lockstep -Mdir "$O/obj" -j "$JOBS" "${COMMON[@]}" +define+TBH=$HH \
  $O/pl_dsdv_svc_rs/dsdv_svc_rs_pl.sv $O/pl_dsdv_svc_rs_entry/dsdv_svc_rs_entry_pl.sv $TB \
  $O/pl_dsdv_svc_rs/libdsdv_svc_rs_pl.a $O/pl_dsdv_svc_rs_entry/libdsdv_svc_rs_entry_pl.a > "$O/build_tb.log" 2>&1 \
  || { tail -30 "$O/build_tb.log"; exit 1; }
sha256sum "${RS_SRC[@]}" $TB tools/s81_dv/svc_rs/rs_files.sh > "$O/sources.sha256"
echo "build done $(date)"
# run every image dir given after the build dir and H: IMGROOT/<name> -> $O/run_<name>_s<seed>.log
shift 2
for IMG in "$@"; do for SEED in ${LS_SEEDS:-1}; do
  n=$(basename "$IMG")
  "$O/obj/Vtb_svc_lockstep" +dir="$IMG" +seed=$SEED > "$O/run_${n}_s$SEED.log" 2>&1 || true
  echo "$n s$SEED: $(grep -h '^LS_END' "$O/run_${n}_s$SEED.log" | tail -1)"
done; done
echo "all done $(date)"
