#!/bin/bash
# DIE-HEAD-44: HEAD die reset contract bench.  bench_head_reset.sh CELLS_SV OUTDIR
# runs the contract (HOLD 64), HOLD 63, the HOLD 61 mutant and the run-only rgate mutant (MUT 1) with Icarus Verilog.
set -u
C=$1; O=$2; H=$(cd "$(dirname "$0")" && pwd); mkdir -p "$O"
for v in "64 0" "63 0" "61 0" "64 1"; do set -- $v
  iverilog -g2012 -P tb.HOLD=$1 -P tb.MUT=$2 -o "$O/r_$1_$2" "$H/tb_head_reset.sv" "$C" || exit 2
  echo "--- HOLD=$1 MUT=$2"; vvp -n "$O/r_$1_$2"
done
