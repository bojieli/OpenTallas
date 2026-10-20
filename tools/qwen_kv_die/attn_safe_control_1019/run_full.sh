#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
python3 tools/qwen_kv_die/attn_safe_control_1019/build_full_bench.py
python3 - <<'PY'
import pathlib,re
p=pathlib.Path('synth/config.mk').read_text();s=re.search(r'export VERILOG_FILES = (.*)',p)[1].replace('/src/','src/').split()
s+=['src/rtl/qwen_sys/kv_bootage_20261019/qkd_attn_result_face_sb.sv','src/rtl/qwen_sys/kv_bootage_20261019/qkd_kvs_attn_ba4.sv','src/rtl/lib/face_land/qkd_kvs_attn_fl_ba4.sv']
pathlib.Path('full/sources.f').write_text('\n'.join(s)+'\n')
PY
verilator --version > full/build.log
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_full --Mdir "$PWD/full/obj" -o vtb full/tb_full.sv -f full/sources.f >> full/build.log 2>&1
full/obj/vtb > full/sim.log 2>&1
grep '^ATTN_FULL_EXACT PASS' full/sim.log
