#!/bin/bash
# Necessary source construction for measured head-context publication roots.
set -euo pipefail
mkdir -p headtx_construct
repo_root=$PWD
out_root=$PWD/headtx_construct
docker run --rm -v "$repo_root:/src:ro" -v "$out_root:/out" -w /src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -p "read_verilog -sv rtl/qwen_split/mu/qfd_mu_head_context_tx.sv; synth -top qfd_mu_head_context_tx -flatten -noabc -nofsm -noshare; write_json /out/original.json" > /out/synth.log 2>&1'
python3 - <<'PY'
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'tools/qwen_split/record32')
import bound_record_graph as B
p=Path('headtx_construct');d=json.loads((p/'original.json').read_text());m=d['modules']['qfd_mu_head_context_tx'];m['ports']['rst_rn']=m['ports'].pop('rst_n');raw=json.dumps(d).encode();(p/'original_reset_alias.json').write_bytes(raw)
s,h,r=B.build(raw,'qfd_mu_head_context_tx','qfd_mu_head_context_tx_lctx32',load_cap=24,retain_all_comb=True)
s=s.replace('qfd_record32_','qfd_headtx32_');h=[x.replace('qfd_record32_','qfd_headtx32_') for x in h]
(p/'qfd_mu_head_context_tx_lctx32.sv').write_text(s);(p/'qfd_mu_head_context_tx_lctx32_helpers.sv').write_text('\n'.join(h)+'\n');(p/'record.json').write_text(json.dumps(r,indent=2)+'\n')
# Existing transition-miter emitter expects the historical component name.
d['modules']['qfd_sys_face_record_port']=d['modules'].pop('qfd_mu_head_context_tx');(p/'transition_original.json').write_text(json.dumps(d)+'\n')
print('HEADTX_CONSTRUCT',r['original_cells'],r['final_cells'],'copies',len(r['input_copies']),'reset_leaves',len(r['reset_leaves']))
PY
python3 tools/qwen_split/record32/prove_transition.py headtx_construct/transition_original.json headtx_construct/record.json headtx_construct/transition.sv > headtx_construct/transition_build.log
docker run --rm -v "$repo_root:/src:ro" -v "$out_root:/out" -w /src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -p "read_verilog /out/transition.sv; prep -top record32_transition -flatten; sat -verify -prove bad 0 -set-def-inputs" > /out/transition_sat.log 2>&1'
echo HEADTX_TRANSITION_PASS
