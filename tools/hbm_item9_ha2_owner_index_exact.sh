#!/usr/bin/env bash
set -euo pipefail
out=$1
[[ "$out" = /* && ! -e "$out" ]]
mkdir -p "$out"
iverilog -g2012 -s tb_item9_ha2_owner_index -o "$out/bench.vvp" \
 rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_item9_cuts.sv \
 results/rtl/hbm_item9_closure_20261005/tb_item9_ha2_owner_index.sv > "$out/build.log" 2>&1
vvp "$out/bench.vvp" > "$out/run.log" 2>&1
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,sys
p=Path(sys.argv[1]);s=(p/'run.log').read_text()
assert 'PASS actualHA2 owner-index exhaustive tests=12583168 zero newcycles' in s,s
f='rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_item9_cuts.sv'
(p/'result.json').write_text(json.dumps(dict(verdict='PASS_ACTUAL_RTL_OWNER_INDEX',tests=12583168,legal_PF_values=list(range(16,385,16)),all_uint16_fragment_indices=True,all_uint8_rank_aliases=True,new_decode_cycles=0,source_sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest()},fullshape_numeric_exact=False,contextual_SS_FF=False,adopted=False),indent=2)+'\n')
PY
