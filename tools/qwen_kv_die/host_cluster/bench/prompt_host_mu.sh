#!/bin/bash
set -eu
OUT=${1:-out_mu};mkdir -p "$OUT"
SOURCE=${2:-rtl/qwen_sys/host_cluster_20261017/prompt_safe/ot_host_if_pb2_observed_ps.sv}
python3 - "$OUT" "$SOURCE" <<'EOF'
from pathlib import Path
import sys
out=Path(sys.argv[1]);s=Path(sys.argv[2]).read_text();import re
s=re.sub(r'module ot_host_if_pb2_observed_ps[0-9]*', 'module ot_host_if_pb2_observed',s)
(out/'pb2.sv').write_text(s)
s=Path('rtl/test/mu_qwen_1018/lists/tb_qkd_host_mu_out.f').read_text().replace('rtl/qwen_sys/host_integrated_20261014/ot_host_if_pb2_observed.sv',str(out/'pb2.sv'))
s+='\nrtl/qwen_sys/host_cluster_20261017/prompt_safe/ot_hkv_prompt_mem.sv\nrtl/qwen_sys/host_cluster_20261017/prompt_pd/ot_hkv_cnt_la.sv\nphysical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v\n'
(out/'sources.f').write_text(s)
EOF
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_qkd_host_mu_out -Mdir "$OUT/obj" -f "$OUT/sources.f" >"$OUT/build.log" 2>&1
"$OUT/obj/Vtb_qkd_host_mu_out" >"$OUT/test.log" 2>&1
cat "$OUT/test.log"
grep -q '^PASS' "$OUT/test.log"
