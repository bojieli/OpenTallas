#!/bin/bash
set -euo pipefail
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --binary --timing --top-module tb_s81sl_rstd_release --build-jobs 2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --Mdir obj_small ot_s81sl_xrt.sv tb_exact_release.sv >small_build.log 2>&1
obj_small/Vtb_s81sl_rstd_release >small_base.log 2>&1
$V --binary --timing --top-module tb_s81sl_rstd_release --build-jobs 2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+OT_S81SL_QREL_MUT_RELEASE --Mdir obj_mut ot_s81sl_xrt.sv tb_exact_release.sv >mut_build.log 2>&1
set +e
obj_mut/Vtb_s81sl_rstd_release >small_mutant.log 2>&1;m=$?
set -e
if [ "$m" -eq 0 ];then exit 1;fi
for hb in 0 1;do
 $V --binary --timing --top-module tb_s81sl_xrt_qrel_eq -GHB=$hb --build-jobs 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --output-split 5000 --Mdir obj_hb$hb ot_rst_relay.sv ot_s81sl_xrt.sv ref_xrt.sv tb_exact_xrt.sv >hb${hb}_build.log 2>&1
 obj_hb$hb/Vtb_s81sl_xrt_qrel_eq >hb${hb}.log 2>&1
 grep -q '^PASS' hb${hb}.log
 tail -3 hb${hb}.log
done
printf 'SMALL_BASE_RC=0\nSMALL_MUTANT_RC=%d\nHB0_RC=0\nHB1_RC=0\n' "$m" >status.txt
cat status.txt
