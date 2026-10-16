#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/vmdel-v6-add0915
rc=0
for m in 0 1 2 3 4 5 6 7;do
 bash tools/hbm_v15_harden/bench_delivery_v6_protocol.sh out$m "$m" > bench$m.log 2>&1
 r=$?; echo "ROW mutant=$m rc=$r";tail -6 bench$m.log
 if [ "$m" = 0 ];then [ "$r" = 0 ] && grep -q 'DELIVERY_V6_PROTOCOL_GATE PASS' bench$m.log || rc=1
 else [ "$r" = 1 ] && grep -q '^FATAL:.*\(V6_PROTOCOL\|clock owner\|clock epoch\)' bench$m.log || rc=1;fi
done
sed 's/module ot_hbm_svc_static_vm_delivery_split_v6 /module ot_hbm_svc_static_vm_delivery /' rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_static_vm_delivery_split_v6.sv > prod.sv
iverilog -g2012 -s tb_hbm_svc_static_vm_delivery -Ptb_hbm_svc_static_vm_delivery.LAT=2 -Ptb_hbm_svc_static_vm_delivery.SLAT=2 -o prod.vvp physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v prod.sv rtl/hbm_accel/loader/service_native/tb_hbm_svc_static_vm_delivery.sv > prod.build.log 2>&1 && vvp prod.vvp > prod.log 2>&1 || rc=1
cat prod.log;grep -q 'STATIC_VM_DELIVERY PASS' prod.log || rc=1
exit $rc
