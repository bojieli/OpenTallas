#!/bin/bash
# redesign-hbm 2026-10-09: exact bench of the pipelined-decode replay SRAM (ot_hbm_replay_sram_dp.sv), run in the source root.
#   bench_dp.sh <outdir> [mut]   mut: sel (stale bank select) | enc (encoder column mutant): the run must FAIL
set -u; O=$1; M=${2:-}; mkdir -p $O; D=rtl/hbm_accel/tu/link_retry_sram_20261008
S="rtl/common/ot_secded.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $D/ot_hbm_replay_sram_dp.sv"
sed 's/if(waitn!=4)\$fatal(1,"response latency%0d expected4",waitn)/if(waitn!=6)$fatal(1,"response latency%0d expected6",waitn)/; s/repeat(6)begin tick/repeat(8)begin tick/' $D/tb_hbm_replay_sram.sv > $O/tb_dp.sv
F=""; [ "$M" = sel ] && F="-DOT_REPLAY_DP_MUT_SEL"; [ "$M" = enc ] && F="-Ptb_hbm_replay_sram.TB_MUT=1"
iverilog -g2012 -Irtl/common -s tb_hbm_replay_sram $F -o $O/unit $S $O/tb_dp.sv && vvp -n $O/unit > $O/unit.log 2>&1; u=$?
tail -2 $O/unit.log; grep -q PASS_ALL $O/unit.log && [ $u = 0 ] || { echo "REPLAY_DP FAIL (unit)"; exit 1; }
[ -n "$M" ] && { echo "REPLAY_DP mutant survived the unit bench"; exit 0; }
OT_RETRY_REPLAY_SRC=$D/ot_hbm_replay_sram_dp.sv OT_RETRY_DEFS=-DOT_RETRY_RSTR python3 tools/hbm_link_retry_pipeline_bench.py --cl --out $O/pipe > $O/pipe.json 2>&1
grep -q '"exactness_gate": "PASS"' $O/pipe.json || { echo "REPLAY_DP FAIL (pipeline)"; exit 1; }
echo "REPLAY_DP PASS (unit: 512 records, correction / poison / tags / back-to-back at latency 6; retry pipeline --cl RSTR PASS_ALL + dup mutant)"
