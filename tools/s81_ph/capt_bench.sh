#!/bin/bash
# CLAUDE S81-PH tiled capture bench (redesign pass 2026-10-06): gather (ROOT_BLK 1, PIPE root) -> dsfd_sp_capture
# (CORE 2 = ot_s81ph_cap_t: 8 x dsfd_capt_grp + dsfd_capt_ctl) vs the W10 roots + rd64 reference,
# tb_s81ph_gather_capture +UNORD (transaction level: per-root write multisets; fault runs fail closed).
# usage (from the source root): tools/s81_ph/capt_bench.sh <out> <tag> "<cases>" [defines...]
#   exit 0 = every case PASS; the summary line "CAPT_BENCH PASS|FAIL" is the verdict.
set -u
OUT=$1; TAG=$2; CASES=$3; shift 3
d=''; for x in "$@"; do d="$d +define+$x"; done
mkdir -p $OUT
for c in $CASES; do
  case $c in mix) a="mix 7";; mix11) a="mix 11";; mix12) a="mix 12";; mix13) a="mix 13";; *) a="$c 7";; esac
  [ -f $OUT/stim_$c.txt ] || python3 rtl/dsrom_sys/s81_ph/test/gen_stim.py $a $OUT/stim_$c.txt
done
timeout 5400 verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
  --top-module tb_s81ph_gather_capture $d -Mdir $OUT/obj_$TAG -o sim \
  rtl/v41rom/ot_v41_ret.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/gpu/ot_fp32_add_rne_deep.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv \
  rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv rtl/dsrom_sys/rd64_capture/ot_dsrom_s81_phase_capture_profile.sv \
  rtl/common/ot_ratio_cdc_fifo.sv rtl/dsrom_sys/s81_ph/ot_s81ph_ret_root_p.sv rtl/dsrom_sys/s81_ph/ot_s81ph_root_blk.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_root_tile.sv rtl/dsrom_sys/s81_ph/ot_s81ph_gather.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_cap_p.sv rtl/dsrom_sys/s81_ph/ot_s81ph_capture.sv rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv \
  rtl/dsrom_sys/s81_ph/dsfd_sp_gather.sv rtl/dsrom_sys/s81_ph/dsfd_sp_capture.sv \
  rtl/dsrom_sys/s81_ph/test/tb_s81ph_gather_capture.sv > $OUT/build_$TAG.log 2>&1 || { echo "CAPT_BENCH FAIL build"; exit 1; }
for c in $CASES; do $OUT/obj_$TAG/sim +UNORD +STIM=$OUT/stim_$c.txt > $OUT/run_${TAG}_$c.log 2>&1 & done
wait
rc=0
for c in $CASES; do
  s="$(grep -h SUMMARY $OUT/run_${TAG}_$c.log) $(grep -h 'RESULT' $OUT/run_${TAG}_$c.log | tail -1)"
  echo "$TAG $c: $s"
  echo "$s" | grep -q 'RESULT PASS' || rc=1
done | tee $OUT/summary_$TAG.txt
grep -q 'RESULT PASS' $OUT/summary_$TAG.txt || true
if grep -v 'RESULT PASS' $OUT/summary_$TAG.txt | grep -q .; then echo "CAPT_BENCH FAIL" | tee -a $OUT/summary_$TAG.txt; exit 1; fi
echo "CAPT_BENCH PASS" | tee -a $OUT/summary_$TAG.txt
