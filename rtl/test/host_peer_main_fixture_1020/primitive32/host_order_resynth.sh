#!/usr/bin/env bash
set -euo pipefail
# Run inside pinned openroad/orfs:asap7lock with this lane mounted at /work.
cd /work
mkdir -p libs
for f in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*.lib.gz; do
  gzip -dc "$f" > "libs/$(basename "${f%.gz}")"
done
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib libs/
python3 - <<'PY'
from pathlib import Path
libs=sorted(Path('libs').glob('*.lib'))
assert libs
cmd=['read_liberty -lib '+str(p) for p in libs]
cmd += ['read_verilog -lib macro_bb.v', 'read_verilog qkd_hr_core_peer_n32.sv',
        'hierarchy -check -top qkd_hr_core_peer_n32',
        'synth -top qkd_hr_core_peer_n32 -noabc',
        'write_verilog -noattr resynth.v']
Path('resynth.ys').write_text('\n'.join(cmd)+'\n')
PY
yosys -s resynth.ys > resynth.log 2>&1
python3 host_order_native32_certificate.py --original original.v --mapped resynth.v --parser textbook_lint.py --record qkd_hr_core_peer_n32.json --out correspondence_resynth.json
