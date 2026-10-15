#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
controller=rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv
source="$d/ot_hbm_svc_native_sector_queued_stack.sv"
for mode in stack production;do
  iverilog -g2012 -s tb -o "$out/$mode.vvp" "$controller" "$source" "$d/tb_hbm_svc_native_sector_queued_$mode.sv"
  vvp "$out/$mode.vvp" > "$out/$mode.log"
done
python3 - "$source" "$out" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();out=Path(sys.argv[2])
for name,old,new in [('enqueue_ACK','if(accepted)begin','if(accepted)begin k_wr_done[p]<=k_we[p];'),('wrong_FIFO_head','head=queue[rp],push=queue[ep]','head=queue[rp+5\'d1],push=queue[ep]')]:
 assert s.count(old)==1
 (out/(name+'.sv')).write_text(s.replace(old,new))
PY
for mutant in enqueue_ACK wrong_FIFO_head;do
  iverilog -g2012 -s tb -o "$out/$mutant.vvp" "$controller" "$out/$mutant.sv" "$d/tb_hbm_svc_native_sector_queued_production.sv"
  if vvp "$out/$mutant.vvp" > "$out/$mutant.log";then echo "mutant unexpectedly passed: $mutant";exit 1;fi
done
grep -q 'enqueue ACK or duplicate WR' "$out/enqueue_ACK.log"
grep -Eq 'queued write payload/identity|native queued controller fault' "$out/wrong_FIFO_head.log"
cat "$out/stack.log" "$out/production.log"
echo 'NATIVE_QUEUED_MUTANTS PASS rejected enqueue_ACK and wrong_FIFO_head'
