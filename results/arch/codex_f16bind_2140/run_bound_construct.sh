#!/bin/bash
set -euo pipefail
mkdir -p bound_construct
python3 - <<'PYS'
from pathlib import Path
src=Path('results/arch/codex_f16bind_2140/sources.txt').read_text().splitlines()
src=[p if not p.endswith('ot_rom_4096x72_m8_iverilog.v') else 'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v' for p in src]
s='read_verilog -sv -DSYNTHESIS -I/src/rtl/qwen_sys/d2d_static_20261015 '+' '.join('/src/'+p for p in src)+'\n'
s+='chparam -set MU 1 -set MU_HEAD 1 -set ROPE 1 -set L_CONTEXTS 1 qfd_sys_face_lctx3_wrapped_f16\n'
s+='synth -top qfd_sys_face_lctx3_wrapped_f16 -flatten -noabc -nofsm -noshare\nwrite_json /out/original.json\n'
Path('bound_construct/front.ys').write_text(s)
PYS
docker run --rm -v "$PWD:/src:ro" -v "$PWD/bound_construct:/out" -w /src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -s /out/front.ys > /out/frontend.log 2>&1'
python3 - <<'PYS'
import importlib.util,json
from pathlib import Path
p=Path('results/arch/codex_f16bind_2140/bound_lctx_full_graph.py');spec=importlib.util.spec_from_file_location('builder',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=Path('bound_construct/original.json').read_bytes()
s,h,d=m.build(raw,'qfd_sys_face_lctx3_wrapped_f16','qfd_sys_face_lctx4_bounded_f16',load_cap=24,transparent_inverters=True,retain_all_comb=True)
assert len([c for c in d['graph']['cells'].values() if c['type']=='ot_rom_4096x72_m8'])==3
Path('bound_construct/qfd_sys_face_lctx4_bounded_f16.sv').write_text(s)
Path('bound_construct/qfd_sys_face_lctx4_f16_helpers.sv').write_text('\n'.join(h)+'\n')
Path('bound_construct/construction.json').write_text(json.dumps(d,indent=2)+'\n')
print('F16_CONSTRUCT',json.dumps({k:d[k] for k in ['original_cells','final_cells','added_by_type','passes']}))
PYS
