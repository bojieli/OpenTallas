#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
for direction in 0 1;do
 if ((direction==0));then wh=512;rh=416.666667;else wh=416.666667;rh=512;fi
 for m in 0 1 2 3 4 5;do
  iverilog -g2012 -s tb_hbm_svc_fault_cdc -Ptb_hbm_svc_fault_cdc.MUT=$m -Ptb_hbm_svc_fault_cdc.WR_HALF=$wh -Ptb_hbm_svc_fault_cdc.RD_HALF=$rh -o "$out/d${direction}_m$m.vvp" rtl/lib/ot_reset_sync.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/tb_hbm_svc_fault_cdc.sv"
  rc=0;vvp "$out/d${direction}_m$m.vvp" > "$out/d${direction}_m$m.log" 2>&1||rc=$?
  if ((m==0));then test "$rc" = 0;grep -q 'PASS STATUS_FIFO' "$out/d${direction}_m$m.log";cat "$out/d${direction}_m$m.log"
  else test "$rc" != 0;grep -q 'STATUS' "$out/d${direction}_m$m.log";echo "STATUS_FIFO mutant$m direction$direction rejected: $(head -1 "$out/d${direction}_m$m.log")";fi
 done
done
