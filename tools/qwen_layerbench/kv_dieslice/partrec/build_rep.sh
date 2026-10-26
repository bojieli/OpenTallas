#!/bin/bash
# build_rep.sh BUILDDIR PART OUT: flat Verilator build of tb_rep_<PART> from the whole-die build's kv3_<PART>_part child
# args (same -y dirs and sources), with probe_<PART>.svh.
set -euo pipefail
B=$1; P=$2; O=$3; H=$(cd $(dirname $0) && pwd); mkdir -p $O
A=$B/obj/Vkv3_${P}_part__hierMkArgs.f
grep -o '"-y" "[^"]*"' $A | tr -d '"' > $O/ydirs.f
grep '^/' $A | grep -v -e 'hier.vlt' -e '/kv_dieslice/' > $O/srcs.f; grep -o '+incdir+[^ "]*' $A >> $O/srcs.f || true
cd $O
/usr/bin/time -v $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 --x-assign fast --x-initial fast \
  -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-MODDUP --timescale 1ns/1ps \
  -j 32 --top-module tb_rep_$P -Mdir obj -f ydirs.f -f srcs.f +define+PROBE +incdir+$H $H/tb_rep_$P.sv \
  -CFLAGS -O1 > build.log 2>&1 || { grep -m5 '%Error' build.log; exit 2; }
echo "PARTREP BUILD OK $O/obj/Vtb_rep_$P $(grep -E 'Elapsed|Maximum res' build.log | tr -s ' ' | tr '\n' ' ')"
