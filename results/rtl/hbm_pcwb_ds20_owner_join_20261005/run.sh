#!/bin/bash
set -u
cd /srv/opentallas-scratch/jobs/sagan-ds20-pcwb-owner-e882f5524-r1/src
iverilog -g2012 -s tb_ds_hbm_pcwb_owner_join -o ../sim rtl/hbm_accel/integration/ot_ds_hbm_pcwb_owner_join.sv rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv rtl/test/hbm_accel/tb_ds_hbm_pcwb_owner_join.sv >../compile.log 2>&1
rc=$?
if [ "$rc" = 0 ]; then vvp ../sim >../run.log 2>&1; rc=$?; fi
printf '%s\n' "$rc" >../exit
exit "$rc"
