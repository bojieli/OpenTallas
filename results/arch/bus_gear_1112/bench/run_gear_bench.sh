#!/bin/bash
# BUS-GEAR-1 bench matrix (iverilog -g2012): real configs + mutants; exit 1 on any unexpected result.
set -u
D=$(cd "$(dirname "$0")" && pwd); RTL=${RTL:-$D/../../../../rtl/common/ot_bus_gear.sv}; TB=$D/tb_ot_bus_gear.sv
O=${OUT:-/tmp/bus_gear_bench.$$}; mkdir -p "$O"; bad=0
run() { # name expect params...
  local n=$1 e=$2; shift 2; local P=""; for p in "$@"; do P="$P -Ptb_ot_bus_gear.$p"; done
  iverilog -g2012 -o "$O/$n.vvp" $P "$RTL" "$TB" || { echo "$n COMPILE-FAIL"; bad=1; return; }
  local r; r=$(vvp -n "$O/$n.vvp" | grep RESULT); echo "$n expect=$e :: $r"
  case "$e:$r" in PASS:*"RESULT PASS"*|FAIL:*"RESULT FAIL"*) ;; *) bad=1;; esac
}
run hbm_wdata_b2_h3   PASS W=288 BEATS=2 H=3 SW=40
run hbm_wdata_b2_h0   PASS W=288 BEATS=2 H=0 SW=40
run hbm_wdata_b4_h3   PASS W=288 BEATS=4 H=3 SW=40
run s81_x_b2_h6       PASS W=1104 BEATS=2 H=6 SW=1
run odd_w_b4_h1       PASS W=1103 BEATS=4 H=1 SW=3
run idx_b2_h2         PASS W=2776 BEATS=2 H=2 SW=1
run mut1_order        FAIL W=288 BEATS=2 H=3 SW=40 MUT=1
run mut1_order_b4     FAIL W=288 BEATS=4 H=3 SW=40 MUT=1
run mut2_sideband     FAIL W=288 BEATS=2 H=3 SW=40 MUT=2
run mut3_nofault      FAIL W=288 BEATS=2 H=3 SW=40 MUT=3
[ $bad = 0 ] && echo "BENCH PASS (6 configs exact, 4 mutants caught)" || { echo "BENCH FAIL"; exit 1; }
