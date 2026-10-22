#!/usr/bin/env bash
# usage: run.sh <master> <W> <AW> [mut]   (from repo root; Verilator 5.050 when present)
set -euo pipefail
M=$1; W=$2; AW=$3; MUT=${4:-}
v=$(command -v verilator || true); for c in /opt/verilator-5.050/bin/verilator $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; do [ -x $c ] && v=$c; done
"$v" --version
O=obj_${M}_${MUT:-pos}; mkdir -p $O
sed "s/\bmodule $M\b/module ot_ref_$M/" physical/asap7_memory_macros/$M/$M.v > $O/ref.v
D=""; [ "$MUT" = mut ] && D="-DMUT"
"$v" --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb -DW=$W -DAW=$AW -DREF=ot_ref_$M -DDUT=$M $D --Mdir $O -o sim \
  rtl/test/sram_p192_1019/tb_p192_equiv.sv $O/ref.v rtl/lib/sram_p192_1019/${M}__p192.sv \
  physical/asap7_memory_macros/${M}_p192_mir/${M}_p192_mir.v > $O/build.log 2>&1 || { tail -20 $O/build.log; exit 3; }
./$O/sim
