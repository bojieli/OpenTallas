#!/usr/bin/env bash
set -euo pipefail
# Run inside pinned openroad/orfs:asap7lock with this lane mounted at /work.
cd /work
TOP=${1:-qkd_hr_core_prompt_n32}
mkdir -p libs
for f in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*.lib.gz; do
  gzip -dc "$f" > "libs/$(basename "${f%.gz}")"
done
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib libs/
python3 - "$TOP" <<'PY'
from pathlib import Path
import sys
top=sys.argv[1]
libs=sorted(Path('libs').glob('*.lib'))
assert libs
cmd=['read_liberty -lib '+str(p) for p in libs]
cmd += ['read_verilog -lib macro_bb.v', 'read_verilog '+top+'.sv',
        'hierarchy -check -top '+top,
        'synth -top '+top+' -noabc',
        'write_verilog -noattr resynth.v']
Path('resynth.ys').write_text('\n'.join(cmd)+'\n')
PY
yosys -s resynth.ys > resynth.log 2>&1
python3 host_prompt_native32_certificate.py --original original.v --mapped resynth.v --parser textbook_lint.py --record "$TOP.json" --out correspondence_resynth.json
