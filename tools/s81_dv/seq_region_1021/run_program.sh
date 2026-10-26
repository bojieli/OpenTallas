#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "$1"); M=${2:-0};mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/s81_dv/seq_region_1021/prep_program.py "$O"
mapfile -t F < "$O/files.txt"
sha256sum "${F[@]}" > "$O/sources.sha256"
"$VL" --version > "$O/verilator.version"
"$VL" --binary --timing -j "${J:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -Wno-TIMESCALEMOD \
 -DDSFD_HOST_C_STATIC -DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10 -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D -DOT_S81_SH_S10E -DTB_HSH=8 -DMUT="$M" \
 --top-module tb_dsdv_seq_host "${F[@]}" --Mdir "$O/obj" > "$O/build.log" 2>&1
set +e
"$O/obj/Vtb_dsdv_seq_host" +seed=1 > "$O/run.log" 2>&1
rc=$?
set -e
cat "$O/run.log"
if [ "$M" = 0 ] && grep -q '^SEQHOST PASS' "$O/run.log";then echo SEQ_REGION_PROGRAM_PASS;exit 0;fi
if [ "$M" = 1 ] && grep -q '^SEQHOST FAIL' "$O/run.log" && grep -q 'MISMATCH vo_s' "$O/run.log";then echo SEQ_REGION_PROGRAM_MISSING_LANDING_CAUGHT;exit 1;fi
echo "SEQ_REGION_PROGRAM_UNCLASSIFIED mutant=$M rc=$rc";exit 2
