#!/usr/bin/env bash
# usage: run.sh <rtl dir> [mutant define]
set -uo pipefail
R=$1; M=${2:-}; D=$(mktemp -d)
pp(){ verilator -E -P "$@" $R/ot_pdie_serdes.sv 2>/dev/null | awk '/^module ot_s81_rate_match/,/^endmodule/'; }
pp -DOT_S81_RM_STAGED -DOT_S81_RM_LOCAL4 | sed 's/^module ot_s81_rate_match/module rm_ref/' > $D/ref.sv
pp -DOT_S81_RM_STAGED -DOT_S81_RM_LOCAL4 -DOT_S81_RM_WFULL8 ${M:+-D$M} | sed 's/^module ot_s81_rate_match/module rm_new/' > $D/new.sv
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb --Mdir $D/obj -o tb $(dirname $0)/tb_w8.sv $D/ref.sv $D/new.sv > $D/build.log 2>&1 || { tail -20 $D/build.log; exit 2; }
$D/obj/tb 2>&1 | grep -v '^- ' | tail -4
