#!/bin/bash
set -euo pipefail
O=$(mkdir -p ../out;cd ../out;pwd)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
S=rtl/hdc/ingest/ot_s81_ing_stream_n32.sv
"$V" --binary --timing -j 4 --top-module tb_sum -Wno-fatal -Wno-WIDTH --Mdir "$O/obj_sum" "$S" tools/s81_dv/shlk_csa_1021/tb_sum.sv > "$O/sum_build.log" 2>&1
"$O/obj_sum/Vtb_sum" > "$O/sum_run.log";cat "$O/sum_run.log"
for k in pos win;do
 D='';test "$k" != win || D=-DOT_N32_MUT_WIN
 "$V" --binary --timing -j 4 --top-module tb_s81_ing_n32_lockstep -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -DOT_N32_ADDR_CSA -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D $D --Mdir "$O/obj_$k" rtl/hdc/ingest/test/tb_s81_ing_n32_lockstep.sv rtl/hdc/ingest/ot_hdc_kv_ingest.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv "$S" physical/asap7_memory_macros_v2/ot_sram_1r1w2c_16x257_m1/ot_sram_1r1w2c_16x257_m1.v > "$O/lockstep_${k}_build.log" 2>&1
 seeds='1 2';test "$k" != win || seeds=1
 for seed in $seeds;do
  "$O/obj_$k/Vtb_s81_ing_n32_lockstep" +seed=$seed +segs=300 > "$O/lockstep_${k}_$seed.log" 2>&1
  grep -E 'PASS LOCKSTEP|FAIL LOCKSTEP' "$O/lockstep_${k}_$seed.log"
  if [ "$k" = pos ];then grep -q '^PASS LOCKSTEP' "$O/lockstep_${k}_$seed.log";else grep -q '^FAIL LOCKSTEP' "$O/lockstep_${k}_$seed.log";fi
 done
done
bash tools/s81_dv/shlk_csa_1021/native.sh
bash tools/s81_dv/shlk_csa_1021/run_seq.sh
echo CSA_SOURCE_PROOF_DONE
