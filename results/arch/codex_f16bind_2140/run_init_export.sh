#!/bin/bash
set -euo pipefail
python3 - <<'PYS'
from pathlib import Path
p=Path('rtl/qwen_split/f16/qfd_sys_face_lctx3_core_f16.sv');s=p.read_text()
assert s.count("init_u0 <= ev_stage && ta == 9'd0;")==1
Path('init_every_stage0.sv').write_text(s.replace("init_u0 <= ev_stage && ta == 9'd0;","init_u0 <= ev_stage && ta[5:0] == 6'd0;"))
Path('init_wrong_sources.txt').write_text(Path('results/arch/codex_f16bind_2140/sources.txt').read_text().replace(str(p),'init_every_stage0.sv'))
PYS
iverilog -g2012 -I rtl/qwen_sys/d2d_static_20261015 -s tb_init_export -o init_selected.vvp -f results/arch/codex_f16bind_2140/sources.txt results/arch/codex_f16bind_2140/tb_init_export.sv > init_compile.log 2>&1
vvp init_selected.vvp > init_selected.log 2>&1
grep -q 'PASS F16_INIT_EXPORT' init_selected.log
if grep -q 'ERROR:' init_selected.log; then cat init_selected.log; exit 1; fi
iverilog -g2012 -I rtl/qwen_sys/d2d_static_20261015 -s tb_init_export -o init_wrong.vvp -f init_wrong_sources.txt results/arch/codex_f16bind_2140/tb_init_export.sv > init_wrong_compile.log 2>&1
if vvp init_wrong.vvp > init_wrong.log 2>&1; then echo 'INIT mutant survived';exit 1;fi
grep -q 'INIT_SELECTOR port=0 arg=100 got=1' init_wrong.log
cat init_selected.log
cat init_wrong.log
