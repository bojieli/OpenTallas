#!/bin/bash
set -eu
OUT=${1:-out_mu};mkdir -p "$OUT"
python3 - "$OUT" <<'EOF'
from pathlib import Path
import sys
out=Path(sys.argv[1]);s=Path('rtl/qwen_sys/host_cluster_20261017/prompt_safe/ot_host_if_pb2_observed_ps.sv').read_text().replace('module ot_host_if_pb2_observed_ps','module ot_host_if_pb2_observed')
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
