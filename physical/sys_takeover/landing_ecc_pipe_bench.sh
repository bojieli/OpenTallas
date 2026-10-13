#!/bin/bash
# el1011-q-kvd 2026-10-12: ot_qfd_kv_landing_ecc PIPE 2 vs PIPE 0 (cycle-shifted) equivalence, both codeword layouts.
#   landing_ecc_pipe_bench.sh pos OUT   exit 0 iff IL 1 / IL 0 x MUT 0 / 1 all EQ PASS
#   landing_ecc_pipe_bench.sh neg OUT   PIPE 2 built with MUT 1 (no correction): exit 0 iff it still matches (expect FAIL)
set -u
MODE=$1; W=$2; mkdir -p "$W"
R=rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv; TB=rtl/test/qwen_system/tb_qfd_landing_ecc_pipe.sv
n=0; t=0
# q13-kvh 2026-10-13: dense / dense_neg = the production-shape throughput run (valid every cycle, single-bit errors only,
# golden-data check + LANDING_DENSE in/out/active_cycles/latency line); dense_neg builds PIPE 2 with MUT 1 (expect FAIL).
DN=0
case "$MODE" in
  pos) set -- "1 0 0" "1 1 0" "0 0 0" "0 1 0";;
  dense) DN=1; set -- "1 0 0" "0 0 0";;
  dense_neg) DN=1; set -- "1 0 1" "0 0 1";;
  *) set -- "1 0 1" "0 0 1";;
esac
for c in "$@"; do read il m mb <<<"$c"; t=$((t+1))
  iverilog -g2012 -P tb_qfd_landing_ecc_pipe.DENSE=$DN -P tb_qfd_landing_ecc_pipe.IL=$il -P tb_qfd_landing_ecc_pipe.MUT=$m -P tb_qfd_landing_ecc_pipe.MUTB=$mb \
    -o "$W/sim_$il$m$mb" "$TB" "$R" >"$W/build_$il$m$mb.log" 2>&1 || { echo "BUILD_FAIL $c"; exit 3; }
  vvp -n "$W/sim_$il$m$mb" >"$W/run_$il$m$mb.log" 2>&1; tail -1 "$W/run_$il$m$mb.log"
  [ $DN = 1 ] && grep '^LANDING_DENSE' "$W/run_$il$m$mb.log"
  grep -q '^EQ PASS' "$W/run_$il$m$mb.log" && n=$((n+1))
done
echo "LANDING_ECC_PIPE $MODE eq $n/$t"; [ $n = $t ]
