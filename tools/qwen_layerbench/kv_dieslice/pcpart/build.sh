#!/bin/bash
# build.sh BUILDDIR OUT [OLDSRC=NEWSRC] [extra verilator args...]: flat Verilator build of tb_pcpart from the whole-die
# build's kv3_pc_part child args (same -y dirs and sources, no hier blocks).  OLDSRC=NEWSRC re-points every source / -y
# path from the staged tree the build used to a patched copy (KV-TOK B: kv42 -> a copy with apply_B.sh applied).
set -euo pipefail
B=$1; O=$2; H=$(cd $(dirname $0) && pwd); mkdir -p $O
A=$B/obj/Vkv3_pc_part__hierMkArgs.f
grep -o '"-y" "[^"]*"' $A | tr -d '"' | sed 's/^-y /-y /' > $O/ydirs.f
grep '^/' $A | grep -v -e 'hier.vlt' -e '/kv_dieslice/' > $O/srcs.f; grep -o '+incdir+[^ "]*' $A >> $O/srcs.f || true
MAP=${3:-}; [[ $MAP == *=* ]] && sed -i "s#${MAP%%=*}#${MAP#*=}#g" $O/ydirs.f $O/srcs.f
EXTRA=("${@:4}")
cd $O
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 --x-assign fast --x-initial fast \
  -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-MODDUP --timescale 1ns/1ps \
  -j 32 --top-module tb_pcpart -Mdir obj -f ydirs.f -f srcs.f $H/../qkd_hbm3e_phy_pc4_bench.sv $H/tb_pcpart.sv \
  "${EXTRA[@]}" -CFLAGS -O1 > build.log 2>&1 || { grep -m5 '%Error' build.log; exit 2; }
echo "PCPART BUILD OK $O/obj/Vtb_pcpart"
