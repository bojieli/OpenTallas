#!/usr/bin/env bash
# S81-P9-FACE: Verilator lint of svc_rs face port variants (repo root).  Usage: rs_fv_lint.sh OUTDIR TOP...
#   TOP = dsdv_svc_rs (all faces), dsdv_svc_rs_fv_<FM>, dsdv_svc_rs_pvso_entry_fv_<FM> (svc_rs_faces.py)
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; shift; mkdir -p "$O"
source tools/s81_dv/svc_rs/rs_files.sh
P=rtl/dsrom_sys/s81_dv/pv_so
for T in "$@"; do
  /usr/bin/time -f "%M kB %e s" "$VL" --lint-only -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module "$T" -I$D \
    -DSVCQ_ENG_FG3 -DOT_SVC_ALLQ "${RS_DEF[@]}" "${RS_SRC[@]}" $D/dsdv_svc_rs_fv.sv $P/dsdv_pv_so_program.sv $P/dsdv_pv_half_join.sv \
    $P/dsdv_pv_so_ingress.sv $P/dsdv_svc_rs_pvso_entry.sv "${RS_LIB[@]}" > "$O/lint_$T.log" 2>&1 || true
  echo "LINT $T errors=$(grep -c '^%Error' "$O/lint_$T.log") warnings=$(grep -c '^%Warning' "$O/lint_$T.log") $(tail -1 "$O/lint_$T.log")"
done
