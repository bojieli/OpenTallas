#!/bin/bash
# TOK-DS-CMP 2026-10-26: L14 compressed-row (T640 = 128 window + 512 selected) svc attention job on the 16 real
# dsdv_svc_rs slices (closing profile protected libs, RTL = origin/main b272ba0ec, 49/49 files == audited 7b910ca728).
# Builds only the tb top (QMAX 8192) against the existing libs, then base s1/s2 + base_safe + selection mutants.
set -uo pipefail
O=/srv/opentallas-scratch2/claude/tok-ds-cmp-1026
L=/srv/opentallas-scratch2/claude/tok-ds/svc_closing_v4/replay_closing
S=/srv/opentallas-scratch2/claude/wt/tok-ds-l14cc-1026
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p $O/run; cd $O
echo "build start $(date)"
"$V" --binary --top-module tb_svc_lower -Mdir "$O/obj" -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --output-split 20000 \
  --output-split-cfuncs 2000 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 -I"$S/rtl/dsrom_sys/s81_dv/svc_rs" -DRS_OBS \
  "$L/pl_dsdv_svc_rs/dsdv_svc_rs_pl.sv" "$L/pl_dsdv_svc_rs_entry/dsdv_svc_rs_entry_pl.sv" "$S/tools/s81_dv/layer_prog/svc/tb_svc_lower.sv" \
  "$L/pl_dsdv_svc_rs/libdsdv_svc_rs_pl.a" "$L/pl_dsdv_svc_rs_entry/libdsdv_svc_rs_entry_pl.a" > "$O/build_tb.log" 2>&1 || { echo BUILD FAIL; tail -20 $O/build_tb.log; exit 1; }
echo "build done $(date)"
sha256sum $S/tools/s81_dv/layer_prog/svc/tb_svc_lower.sv $S/tools/s81_dv/layer_prog/lower_svc.py $L/pl_dsdv_svc_rs/libdsdv_svc_rs_pl.a $L/pl_dsdv_svc_rs_entry/libdsdv_svc_rs_entry_pl.a > $O/sources.sha256
run() { "$O/obj/Vtb_svc_lower" +dir="$O/img/$1" +seed=$2 > "$O/run/run_$1_s$2.log" 2>&1; echo "$1 s$2: $(grep -h '^SVCLOW ' $O/run/run_$1_s$2.log | tail -1 | grep -o 'verdict=[A-Z]*') $(date)"; }
run base 1 & run base 2 & run base_safe 1 & run sel_id 1 & run rows_pair 1 & run pio_early 1 &
wait
echo "all done $(date)"
