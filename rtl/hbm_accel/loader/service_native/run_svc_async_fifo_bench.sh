#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
for depth in 4 8; do
 for direction in 0 1; do
  if ((direction==0));then wh=512;rh=416.666667;else wh=416.666667;rh=512;fi
  iverilog -g2012 -s tb_hbm_svc_async_fifo -Ptb_hbm_svc_async_fifo.DEPTH=$depth -Ptb_hbm_svc_async_fifo.WR_HALF=$wh -Ptb_hbm_svc_async_fifo.RD_HALF=$rh -o "$out/d${depth}_${direction}.vvp" rtl/lib/ot_reset_sync.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/tb_hbm_svc_async_fifo.sv"
  vvp "$out/d${depth}_${direction}.vvp" > "$out/d${depth}_${direction}.log"
  grep -q 'PASS HBM_FIFO' "$out/d${depth}_${direction}.log"
 done
done
sed 's/mem\[rd_bin\[AW-1:0\]\]/mem[rd_bin[AW-1:0] ^ 1]/' "$d/ot_hbm_svc_async_fifo.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_async_fifo.sv";then echo 'mutant not applied';exit 1;fi
iverilog -g2012 -s tb_hbm_svc_async_fifo -o "$out/mutant.vvp" rtl/lib/ot_reset_sync.sv "$out/mutant.sv" "$d/tb_hbm_svc_async_fifo.sv"
if vvp "$out/mutant.vvp" > "$out/mutant.log";then echo 'FIFO address mutant passed';exit 1;fi
grep -q 'FIFO payload/order mismatch' "$out/mutant.log"
cat "$out"/d*.log
echo 'HBM_FIFO MUTANT rejected address permutation'
