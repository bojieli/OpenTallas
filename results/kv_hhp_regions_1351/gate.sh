#!/bin/bash
set -euo pipefail
W=$(git rev-parse --show-toplevel)
OUT=${1:?scratch output}
mkdir -p "$OUT"
python3 - "$W" "$OUT" <<'PYS'
from pathlib import Path
import sys
w=Path(sys.argv[1]);o=Path(sys.argv[2]);sys.path.insert(0,str(w/'physical/die_plan/qwen_kvsys/cores/harden'))
from kvspc_own_regions import transform
g=(w/'results/kv_hhp_regions_1351/rtl/qkd_static_kv_pc_es_merge_b.sv').read_text()
(o/'gold.sv').write_text(g.replace('module qkd_static_kv_pc_es_merge_b','module own_gold'))
for n,m in [('new',False),('mut',True)]:
 (o/(n+'.sv')).write_text(transform(g,m).replace('module qkd_static_kv_pc_es_merge_b','module own_dut'))
PYS
for n in new mut; do
  iverilog -g2012 -s tb -o "$OUT/$n.vvp" "$OUT/gold.sv" "$OUT/$n.sv" "$W/results/kv_hhp_regions_1351/rtl/qkd_static_kv_pc_es_merge.sv" "$W/results/kv_hhp_regions_1351/rtl/qkd_embedding_static_map.sv" "$W/results/kv_hhp_regions_1351/tb.sv" >"$OUT/$n.build.log" 2>&1
  set +e
  vvp "$OUT/$n.vvp" >"$OUT/$n.log" 2>&1
  rc=$?
  set -e
  cat "$OUT/$n.log"
  if [ "$n" = new ]; then test $rc = 0; else test $rc != 0; fi
done
