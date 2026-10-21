#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
O="$PWD/results/rtl/qw_head_safe32_1020/bench"
mkdir -p "$O"
verilator --version > "$O/verilator.version"
python3 - <<'PY'
import ast,json,hashlib
from pathlib import Path
p=Path('tools/uarch_model.py');tree=ast.parse(p.read_text());f=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='qwen_head_fifo4_sram_safe32_model');ns={};exec(compile(ast.Module(body=[f],type_ignores=[]),str(p),'exec'),ns)
m=ns[f.name]();m['model_source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
Path('results/rtl/qw_head_safe32_1020/model.json').write_text(json.dumps(m,indent=2)+'\n')
PY
for m in 0 1 2 3 4;do
 verilator --cc --exe --build -j 8 -O2 --top-module tb --prefix Vtb -GMUT=$m -Wno-fatal -Wno-WIDTH \
  --Mdir "$O/obj_m$m" "$PWD/results/rtl/qw_head_safe32_1020/tb_fifo.sv" \
  "$PWD/rtl/qwen_sys/static_schedule_20261014/safe32/ot_qfd_head_fifo4_sram.sv" \
  "$PWD/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v" \
  "$PWD/rtl/test/qwen_dv/main2.cpp" > "$O/build_m$m.log" 2>&1
 "$O/obj_m$m/Vtb" > "$O/m$m.log" 2>&1
done
