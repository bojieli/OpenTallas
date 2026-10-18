#!/usr/bin/env bash
# H-NETLIST/D4F-RELAY: per-lane lockstep bench of a d4f relay layer: positive PASS, mutants lane_stage / bitswap / branch_drop FAIL.
#   run_relay_lockstep.sh LAYER.json.gz OUT [MAX_BUSES]
set -uo pipefail
L=$1; OUT=$(realpath -m "$2"); MB=${3:-0}; mkdir -p "$OUT"; fail=0
D=rtl/hbm_accel/die_glue
src=($D/hbfd_rly_fc_masters.sv $D/hbfd_rly_fcf_masters.sv $D/hbfd_rly_masters.sv $D/ot_hbm_rly_fc.sv $D/ot_hbm_rly_fcf.sv $D/ot_hbm_rly.sv rtl/lib/ot_rst_relay.sv)
sha256sum "${src[@]}" "$L" tools/hbm_die_v16/relay_lockstep_bench.py > "$OUT/sources.sha256"
for m in pos lane_stage bitswap branch_drop; do
  X=; [ $m != pos ] && X="--mut $m"
  python3 tools/hbm_die_v16/relay_lockstep_bench.py --layer "$L" --out "$OUT/$m" --max-buses $MB $X > "$OUT/$m.gen.log" || { cat "$OUT/$m.gen.log"; fail=1; continue; }
  iverilog -g2012 -o "$OUT/$m/sim" "${src[@]}" "$OUT/$m/tb_relay_lockstep.sv" > "$OUT/$m.build.log" 2>&1 || { tail -5 "$OUT/$m.build.log"; fail=1; continue; }
  r=$(timeout 3000 vvp "$OUT/$m/sim" | grep -E 'RELAY_LOCKSTEP|MISMATCH' | tail -2); echo "$m $(tail -1 $OUT/$m.gen.log) :: $r"
  if [ $m = pos ]; then echo "$r" | grep -q "RELAY_LOCKSTEP PASS" || fail=1; else echo "$r" | grep -Eq "RELAY_LOCKSTEP FAIL checks=[0-9]+ errors=[1-9]" || fail=1; fi
done
[ $fail = 0 ] && echo RELAY_LOCKSTEP_GATE PASS || { echo RELAY_LOCKSTEP_GATE FAIL; exit 1; }
