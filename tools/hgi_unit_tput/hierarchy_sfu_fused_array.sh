#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
python3 - <<'PY'
import os
from pathlib import Path
f='physical/ref_tile/sfu_lane_ring3_rt/src/'
s=[f+p for p in (Path(os.environ['DATA'])/'sources.f').read_text().splitlines()]
s += ['rtl/hbm_accel/generic/peers/ot_hgi_sfu_fused_glu_'+p+'.sv' for p in ['lane','store','array']]
cmd='read_verilog -sv '+ ' '.join(s)+'\n'
cmd+='read_verilog -lib physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v\n'
cmd+='hierarchy -check -top ot_hgi_sfu_fused_glu_array\nproc\ncheck\nstat -width\n'
(Path(os.environ['OUT'])/'hierarchy.ys').write_text(cmd)
PY
yosys -Q -s "$OUT/hierarchy.ys" > "$OUT/hierarchy.log" 2>&1
if grep -q 'ERROR:' "$OUT/hierarchy.log";then tail -30 "$OUT/hierarchy.log";exit 1;fi
printf 'PASS actual256lane96SRAM unflattened Yosys source hierarchy/check; no physical/rate claim\n'
