#!/usr/bin/env bash
# Source-only structural equivalence. No physical or die qualification claim.
set -euo pipefail
MODE=${1:?pass|mut_gate|mut_valid};OUT=${2:?output};mkdir -p "$OUT"
R=$(cd "$(dirname "$0")/../.."&&pwd)
D=$R/rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_partitioned.sv
ARGS=();PAIRS='2:2 0:0 3:4 7:7 9:8'
case "$MODE" in
 pass);;
 mut_gate)ARGS=(-DOT_CFIFO_SPLIT_MUT_GATE);PAIRS='2:2';;
 mut_valid)sed 's/\.v(a\[0\])/\.v(b[0])/' "$D" > "$OUT/dut_mut.sv";cmp -s "$D" "$OUT/dut_mut.sv" && exit 3;D=$OUT/dut_mut.sv;PAIRS='2:2';;
 *)exit 2;;
esac
for pair in $PAIRS;do
 a=${pair%:*};b=${pair#*:}
 iverilog -g2012 "${ARGS[@]}" -s tb_cfifo_partitioned -Ptb_cfifo_partitioned.PHA="$a" -Ptb_cfifo_partitioned.PHB="$b" -o "$OUT/sim_$a$b" "$R/rtl/dsrom_sys/s81_die_bind/test/tb_cfifo_partitioned.sv" "$D" "$R/rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_x2pair.sv" "$R/rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress.sv" "$R/rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv"
 vvp "$OUT/sim_$a$b" > "$OUT/run_$a$b.log" 2>&1 || { cat "$OUT/run_$a$b.log";exit 1; }
 tail -1 "$OUT/run_$a$b.log"
done
