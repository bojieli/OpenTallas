#!/bin/bash
# tu-retry-1010 2026-10-10: standalone retry-port credit bench (tb_hbm_tu_retry_port: its producer is NOT credit-limited,
# so the port's own source-credit counter binds; the bench checks sent - popped <= 256 independently of the DUT).
#   tu_port_credit_bench.sh pos|ovr|free <workdir> [extra iverilog defs...]
#   pos : -DOT_TU_CPIPE, must PASS_ALL                                   -> TPC_PASS rc0
#   ovr : -DOT_TU_CPIPE -DOT_TU_CPIPE_OVR_MUT (put charged one edge late) -> must hit the bench's overflow check: TPC_NEG_FAIL rc1
#   ret : -DOT_TU_CPIPE -DOT_TU_CPIPE_RET_MUT (over-return check removed) -> the forged future pop must be caught: TPC_NEG_FAIL rc1
#   base: CPIPE=0 regression, must PASS_ALL -> TPC_PASS rc0
#   anything unexpected -> TPC_BENCH_ERROR rc2
set -u
M=$1; W=$2; shift 2; mkdir -p "$W"; W=$(cd "$W" && pwd)
L=rtl/hbm_accel/tu/link_retry_sram_20261008
S="rtl/common/ot_secded.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $L/ot_hbm_replay_sram.sv $L/ot_hbm_link_retry_sram.sv $L/ot_hbm_tu_retry_port.sv $L/tb_hbm_tu_retry_port.sv"
case $M in pos) D="-DOT_TU_CPIPE";; ovr) D="-DOT_TU_CPIPE -DOT_TU_CPIPE_OVR_MUT";; ret) D="-DOT_TU_CPIPE -DOT_TU_CPIPE_RET_MUT";; base) D="";; *) echo TPC_BENCH_ERROR mode; exit 2;; esac
iverilog -g2012 $D "$@" -I rtl/common -s tb_hbm_tu_retry_port -o $W/t.vvp $S > $W/build.log 2>&1 || { cat $W/build.log; echo TPC_BENCH_ERROR build; exit 2; }
vvp $W/t.vvp > $W/run.log 2>&1; tail -6 $W/run.log
case $M in
 pos|base) grep -q '^PASS_ALL' $W/run.log && ! grep -qiE 'fatal' $W/run.log && { echo TPC_PASS; exit 0; }; echo TPC_BENCH_ERROR positive; exit 2;;
 ret) grep -q 'forged future popcredit accepted' $W/run.log && ! grep -q '^PASS_ALL' $W/run.log && { echo TPC_NEG_FAIL forged-return-detected; exit 1; }; echo TPC_BENCH_ERROR "over-return mutant escaped"; exit 2;;
 ovr) grep -q 'conserved landing debt overflow\|full actual landing credit count' $W/run.log && ! grep -q '^PASS_ALL' $W/run.log && { echo TPC_NEG_FAIL credit-overrun-detected; exit 1; }; echo TPC_BENCH_ERROR "credit-overrun mutant escaped"; exit 2;;
esac
