#!/usr/bin/env bash
# LB2-S81/CC-svc: build + run the svc attention-job bench (tb_svc_lower.sv) on the images lower_svc.py emits.
#   step 1: dsdv_svc_rs / dsdv_svc_rs_entry protect-libs (base RTL, DIE 0, ST 0 = die.v), as tools/s81_dv/svc_rs/rs_bench_pl.sh;
#   step 2: tb_svc_lower against the two wrappers;  step 3: base (seeds 1 2) + compiler mutants slot / late or pio_early
#   (seed 1, whichever image dirs exist).  MUTDEF=NAME builds the slices with -DNAME (an RTL mutant, e.g. RS_MUT_P) and
#   runs base seed 1 only.
# Usage (repo root): tools/s81_dv/layer_prog/svc/run_svc_bench.sh OUTDIR IMGDIR      (IMGDIR/{base,slot,late}/)
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$(realpath -m "$1"); IMG=$2; JOBS=${JOBS:-8}   # absolute: the tb link runs inside $O/obj
source tools/s81_dv/svc_rs/rs_files.sh
mkdir -p "$O"
"$VL" --version > "$O/verilator.version"
COMMON=(-Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 2000 -fno-inline
        --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 -I$D -DRS_OBS -DSVCQ_ENG_FG3
        "${RS_DEF[@]}" -DMUT=0 ${MUTDEF:+-D$MUTDEF})
lib() {
  local L=$O/pl_$1
  [ -f "$L/lib$1_pl.a" ] && return 0
  "$VL" --cc --build -j "$JOBS" --protect-lib "$1_pl" --top-module "$1" -Mdir "$L" \
    -GMUT=0 -GDIE_ID=0 -GST=0 "${COMMON[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" > "$O/build_$1.log" 2>&1
}
TB=tools/s81_dv/layer_prog/svc/tb_svc_lower.sv
if [ ! -x "$O/obj/Vtb_svc_lower" ]; then
  echo "build start $(date)"
  lib dsdv_svc_rs & P1=$!; lib dsdv_svc_rs_entry & P2=$!
  wait $P1 || { tail -30 "$O/build_dsdv_svc_rs.log"; exit 1; }; wait $P2 || { tail -30 "$O/build_dsdv_svc_rs_entry.log"; exit 1; }
  "$VL" --binary --top-module tb_svc_lower -Mdir "$O/obj" -j "$JOBS" "${COMMON[@]}" \
    $O/pl_dsdv_svc_rs/dsdv_svc_rs_pl.sv $O/pl_dsdv_svc_rs_entry/dsdv_svc_rs_entry_pl.sv $TB \
    $O/pl_dsdv_svc_rs/libdsdv_svc_rs_pl.a $O/pl_dsdv_svc_rs_entry/libdsdv_svc_rs_entry_pl.a > "$O/build_tb.log" 2>&1 \
    || { tail -30 "$O/build_tb.log"; exit 1; }
  echo "build done $(date)"
fi
sha256sum "${RS_SRC[@]}" rtl/dsrom_sys/s81_ph/svc/dsfd_svc_c.sv $D/dsdv_svc_rs_roles.svh $D/dsdv_svc_sx_roles.svh $TB \
  tools/s81_dv/svc_rs/rs_files.sh tools/s81_dv/layer_prog/svc/run_svc_bench.sh > "$O/sources.sha256"
run() {  # $1 image, $2 seed
  "$O/obj/Vtb_svc_lower" +dir="$IMG/$1" +seed=$2 > "$O/run_$1_s$2.log" 2>&1 || true
  echo "$1 s$2: $(grep -h '^SVCLOW ' "$O/run_$1_s$2.log" | tail -1 | grep -o 'verdict=[A-Z]*')"
}
if [ -n "${MUTDEF:-}" ]; then run base 1; echo "all done $(date)"; exit 0; fi
run base 1 & run base 2 & run slot 1 &
for m in late pio_early; do [ -d "$IMG/$m" ] && run $m 1 & done
wait
echo "all done $(date)"
