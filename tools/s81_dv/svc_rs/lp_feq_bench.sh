#!/usr/bin/env bash
# PL-SVC (10-18): lockstep of the original slice vs its wires-only refactor (the lp.py input):
#   ENTRY 0: dsdv_svc_rs vs dsdv_svc_rs_f;  ENTRY 1: dsdv_svc_rs_entry vs dsdv_svc_rs_entry_f (default SID 5 for ENTRY 1)
#   bash tools/s81_dv/svc_rs/lp_feq_bench.sh OUTDIR [FEQ_MUT] [SID] [ENTRY]  (FEQ_MUT 1 = refactor sid off by one: must FAIL)
# Run on the FLEET (ot-run --mem 64), never on localhost.  Prints "FEQ PASS|FAIL ..." and FEQ_EXIT.
set -u
cd "${LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}"
O=$1; M=${2:-0}; E=${4:-0}; SID=${3:-$([ "$E" = 1 ] && echo 5 || echo 9)}; mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
source tools/s81_dv/svc_rs/rs_files.sh
D=rtl/dsrom_sys/s81_dv/svc_rs
"$VL" --binary -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --unroll-count 16 --unroll-limit 131072 \
  --output-split 20000 --output-split-cfuncs 2000 -fno-inline -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 \
  --top-module tb_dsdv_svc_rs_feq -GFEQ_MUT=$M -GSID=$SID -GENTRY=$E -I$D -DSVCQ_ENG_FG3 "${RS_DEF[@]}" "${RS_SRC[@]}" \
  rtl/dsrom_sys/s81_ph/svc/dsfd_svc_c.sv $D/dsdv_svc_rs_glue.sv $D/dsdv_svc_rs_f.sv $D/dsdv_svc_rs_entry_f.sv $D/test/tb_dsdv_svc_rs_feq.sv \
  -Mdir "$O/obj" > "$O/build.log" 2>&1 && "$O/obj/Vtb_dsdv_svc_rs_feq" > "$O/run.log" 2>&1
r=$(grep -o '^FEQ [A-Z]*' "$O/run.log" 2>/dev/null | head -1); grep -h '^FEQ' "$O/run.log" 2>/dev/null
echo "FEQ_MUT $M ENTRY $E SID $SID: ${r:-NO_RESULT (see $O/build.log)}"
if [ "$M" = 0 ]; then [ "$r" = "FEQ PASS" ]; else [ "$r" = "FEQ FAIL" ]; fi; rc=$?
echo "FEQ_EXIT $rc"; exit $rc
