#!/bin/bash
# cont-takeover 2026-10-09: TU PHY retry port exact bench (tb_hbm_tu_retry_phy_port) with REG_IO=1 (-DOT_TU_REG_IO) + mutant.
#   tu_bench.sh pos|neg <workdir>   -> TUB_PASS rc0 / TUB_NEG_FAIL rc1 / TUB_BENCH_ERROR rc2
set -u
M=$1; W=$2; mkdir -p "$W"; W=$(cd "$W" && pwd)
L=rtl/hbm_accel/tu/link_retry_sram_20261008
S="rtl/common/ot_secded.sv $L/ot_hbm_replay_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $L/ot_hbm_link_retry_sram.sv $L/ot_hbm_retry_pop_cdc.sv"
T="$L/ot_hbm_tu_retry_port.sv $L/ot_hbm_tu_retry_phy_port.sv $L/tb_hbm_tu_retry_phy_port.sv"
if [ $M = pos ]; then I=$L/ot_hbm_retry_phy_ingress.sv
else I=$W/mut.sv; python3 - $L/ot_hbm_retry_phy_ingress.sv $I <<'PY' || { echo TUB_BENCH_ERROR needle; exit 2; }
import sys; s=open(sys.argv[1]).read(); a="assign out_data=head[hp];"; assert a in s; open(sys.argv[2],'w').write(s.replace(a,"assign out_data=head[hp+1'b1];",1))
PY
fi
iverilog -g2012 -DOT_TU_REG_IO -I rtl/common -s tb_hbm_tu_retry_phy_port -o $W/t.vvp $S $I $T > $W/build.log 2>&1 || { cat $W/build.log; echo TUB_BENCH_ERROR build; exit 2; }
vvp $W/t.vvp > $W/run.log 2>&1; cat $W/run.log | tail -6
if [ $M = pos ]; then grep -q '^PASS_ALL' $W/run.log && ! grep -qi fatal $W/run.log && { echo TUB_PASS; exit 0; }; echo TUB_BENCH_ERROR positive; exit 2
else grep -qE 'FATAL|mismatch|order' $W/run.log && { echo TUB_NEG_FAIL; exit 1; }; echo TUB_BENCH_ERROR "mutant escaped"; exit 2; fi
