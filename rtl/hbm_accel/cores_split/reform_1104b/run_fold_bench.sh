#!/usr/bin/env bash
# DIE-HEAD-85/TXF 2026-11-07: FOLD = 1 vs FOLD = 0 lock-step bench (CHS 1 = HEAD kit, CHS 0), rs544 frame check of the
# FOLD stream, mutants 1/2/4/5 must FAIL.  All simulations run in parallel (iverilog ~0.6 cycle/s on this design).
#   run_fold_bench.sh [OUTDIR]   (repo root = ../../../..)
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; root="$(cd "$here/../../../.." && pwd)"
out="${1:-$here/fold_bench}"; mkdir -p "$out"
inc=(-g2012 -I"$here" -I"$root/rtl/dsrom_sys/s81_link")
src=("$here/tb_kp4_enc_fold.sv" "$here/ot_s81_kp4_enc_la.sv" "$root/rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv")
for chs in 1 0; do for mut in 0 1 2 4 5; do
  [ -x "$out/b_c${chs}_m$mut" ] || iverilog "${inc[@]}" -s tb_kp4_enc_fold -Ptb_kp4_enc_fold.MUT=$mut -Ptb_kp4_enc_fold.CHS=$chs -o "$out/b_c${chs}_m$mut" "${src[@]}" &
done; done; wait
pids=()
run() { local log=$1; shift; vvp "$@" > "$out/$log.log" 2>&1 & pids+=($!); }
for chs in 1 0; do
  run c${chs}_continuous "$out/b_c${chs}_m0" +NCYC=1600 +SEED=41 +DUMP="$out/dump_c${chs}.txt"
  run c${chs}_stall_reset "$out/b_c${chs}_m0" +NCYC=1600 +SEED=709 +STALL=439 +RESET_AT=900
  run c${chs}_reset_odd "$out/b_c${chs}_m0" +NCYC=1200 +SEED=5 +RESET_AT=503
  for mut in 1 2 4 5; do run c${chs}_mut$mut "$out/b_c${chs}_m$mut" +NCYC=400 +SEED=97; done
done
wait "${pids[@]}"
fail=0
for chs in 1 0; do
  for t in continuous stall_reset reset_odd; do
    l=$(grep -h TB_KP4_ENC_FOLD "$out/c${chs}_$t.log"); echo "$t: $l"; case "$l" in *PASS*) ;; *) fail=1;; esac
  done
  python3 -I "$root/tools/s81_link/check_kp4_dump.py" "$out/dump_c${chs}.txt" --min 100 || fail=1
  for mut in 1 2 4 5; do
    l=$(grep -h TB_KP4_ENC_FOLD "$out/c${chs}_mut$mut.log")
    case "$l" in *FAIL*) echo "MUTANT $mut CHS=$chs CAUGHT: $l";; *) echo "MUTANT $mut CHS=$chs SURVIVED: $l"; fail=1;; esac
  done
done
[ $fail = 0 ] && echo FOLD_BENCH_ALL_PASS || { echo FOLD_BENCH_FAIL; exit 1; }
