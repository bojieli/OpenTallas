#!/bin/bash
# HBM-LANDING 10-18: post-GRT die clock check of a finished d4g (GEN0/GEN1/...) die_case_v16 case at TT AND FF.
#   d4g_dcc_ttff.sh CASE_DIR [SRC_ROOT]     (run on the host holding CASE_DIR; SRC_ROOT = a source tree with tools/)
# Needs CASE_DIR/out/die_clock_dump.tsv (written by run.tcl: die_clock_check.tcl in the dual-corner tt+ff STA session).
# FF arrivals: CASE_DIR/out/die_clock_dump_ff.tsv if present (separate FF session), else the dump's arr_min column
# (= FF in the define_corners tt ff session).  Verdict = TT AND FF pin-arrival skew <= 80 ps on every communicating
# same-root pair within NEAR um (default 405); landed lane pairs (hbfd_land*/hbfd_lh*) are judged by the die STA
# landing window instead (LANDING-CONTRACT L5).  Writes out/neighbour_skew_gate_ttff.{json,log}; exit 0 PASS, 1 FAIL,
# 2 no data / no FF.
C=${1:?case dir}; S=${2:-$(cd "$(dirname "$0")/../.." && pwd)}
[ -s "$C/out/die_clock_dump.tsv" ] || { echo "DCC_TTFF NO_DUMP $C/out/die_clock_dump.tsv"; exit 2; }
mkdir -p "$C/dcc_ttff/hbm_die_v15" || exit 2
cp "$S/tools/die_clock_check.py" "$C/dcc_ttff/" && cp "$S/tools/hbm_die_v15/neighbour_skew_gate.py" "$S/tools/hbm_die_v15/die_clock_tree.py" "$C/dcc_ttff/hbm_die_v15/" || exit 2
python3 -I "$C/dcc_ttff/hbm_die_v15/neighbour_skew_gate.py" --run "$C/out" --near-um "${NEAR:-405}" --budget-ps 80 \
  --ff-from-min --require-ff --out "$C/out/neighbour_skew_gate_ttff.json" > "$C/out/neighbour_skew_gate_ttff.log" 2>&1
rc=$?; head -12 "$C/out/neighbour_skew_gate_ttff.log"; echo "DCC_TTFF rc=$rc $C"; exit $rc
