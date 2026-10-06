#!/usr/bin/env bash
# One die's 32 finite caller register slices, mux and one endpoint; no SM array.
set -euo pipefail
out=$1
[[ "$out" = /* && ! -e "$out" ]]
mkdir -p "$out"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal \
 --top-module tb_item9_context32 -Mdir "$out/obj" \
 rtl/gpu_sys/ot_gpu_reset_ctrl.sv rtl/link/ot_link_afifo.sv \
 rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv rtl/gpu_sys/ot_gpu_coll_mux_f12.sv \
 rtl/gpu_sys/ot_gpu_coll_mux_owner64.sv rtl/gpu_sys/ot_gpu_coll_endpoint_f12_cuts.sv \
 rtl/gpu_sys/ot_gpu_coll_item9_context32.sv \
 results/rtl/hbm_item9_closure_20261005/tb_item9_context32.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_item9_context32" > "$out/run.log" 2>&1
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,re,sys,subprocess
p=Path(sys.argv[1]);s=(p/'run.log').read_text()
m=re.search(r'PASS actual32 caller NL128 exact completed=32 TXrecords=128 RXrecords=256 cycles=(\d+) added_cycles=0',s)
assert m,s
sources=['rtl/gpu_sys/ot_gpu_coll_item9_context32.sv','rtl/gpu_sys/ot_gpu_coll_endpoint_f12_cuts.sv','rtl/gpu_sys/ot_gpu_coll_mux_owner64.sv','results/rtl/hbm_item9_closure_20261005/tb_item9_context32.sv']
(p/'result.json').write_text(json.dumps(dict(verdict='PASS_ACTUAL32_CALLER_ENDPOINT_GATHER_EXACT',completed_callers=32,TX_records=128,RX_records=256,cycles=int(m[1]),added_cycles=0,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in sources},scope='original item9 SIMT caller slice; ordered native gather RX ranks0/1; NOT measured DS sm_v/TU equivalence',contextual_SS_FF=False,adoption=False),indent=2)+'\n')
PY
