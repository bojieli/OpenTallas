#!/bin/bash
set -euo pipefail
vbin=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p out2
"$vbin" --version > out2/verilator.version
/usr/bin/time -v "$vbin" --binary --timing -Wno-fatal -j 4 --top-module tb_qfd_dv_calendar_cap1_install -GNU=4 -GUVM_STRIDE=4096 -GPIDX_STRIDE=128 -Mdir "$PWD/out2/obj" source/*.sv source/*.v boot_probes.sv > out2/build.log 2>&1
for case in cap1_nominal cap1_payload_digest_mut cap1_clear_cap_mut cap1_auth_digest_mut cap1_early_execution_mut cap1_missing_final_drain_mut;do
 set +e
 /usr/bin/time -v out2/obj/Vtb_qfd_dv_calendar_cap1_install "+EV=$PWD/inputs/$case.ev" "+LOG=$PWD/out2/$case.trace" +NCYC=5000 "+OT_ROM_DIR=$PWD/inputs/image_cap1" > "out2/$case.out2" 2>&1
 rc=$?
 set -e
 echo "$case $rc" >> out2/exit_codes.txt
 if [ "$case" = cap1_nominal ];then test "$rc" = 0;else test "$rc" != 0;fi
done
