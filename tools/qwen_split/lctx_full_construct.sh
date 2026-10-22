#!/bin/bash
set -euo pipefail
mkdir -p full_construct
python3 - <<'PY'
from pathlib import Path
s=Path('results/arch/codex_sysface_l_2000/wrapper_sources.f').read_text().splitlines()
a='read_verilog -sv -DSYNTHESIS -I/src/rtl/qwen_sys/d2d_static_20261015 '+ ' '.join('/src/'+x for x in s)+'\n'
a+='chparam -set MU 1 -set MU_HEAD 1 -set ROPE 1 -set L_CONTEXTS 1 qfd_sys_face_lctx3_wrapped\n'
a+='synth -top qfd_sys_face_lctx3_wrapped -flatten -noabc -nofsm -noshare\nwrite_json /out/original.json\n'
Path('full_construct/front.ys').write_text(a)
PY
docker run --rm -v "$PWD:/src:ro" -v "$PWD/full_construct:/out" -w /src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -s /out/front.ys > /out/frontend.log 2>&1'
python3 tools/qwen_split/bound_lctx_full_graph.py full_construct/original.json --top qfd_sys_face_lctx3_wrapped --out full_construct > full_construct/construction.log
echo LCTX_FULL_CONSTRUCT_COMPLETE
