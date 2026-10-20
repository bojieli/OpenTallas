#!/bin/bash
set -eu
D=/srv/opentallas-scratch2/claude/qw-sysface4-1020/native6b
SRC=$D/src
OUT=$D/out
mkdir -p "$OUT"
python3 - "$SRC" <<'CHECK'
import sys,json,hashlib
from pathlib import Path
p=Path(sys.argv[1]);j=json.loads((p/'SOURCE_SHA256.json').read_text())
for rel,h in j.items():
 q=p/rel
 assert hashlib.sha256(q.read_bytes()).hexdigest()==h,rel
print('FULL_SOURCE_STAGING_SHA_PASS',len(j))
CHECK
cp "$D/config.mk" "$D/input.sdc" "$OUT/"
docker run --rm -v "$SRC:/src:ro" -v "$OUT:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -c 'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_HOME=/OpenROAD-flow-scripts/flow synth' > "$OUT/synth.log" 2>&1
docker run --rm -v "$SRC:/src:ro" -v "$OUT:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -c 'python3 /src/tools/ref_tile/native_census.py --netlist /work/results/asap7/qfd_sys_face_n32_bounded/base/1_2_yosys.v --top qfd_sys_face_n32_bounded $(find /OpenROAD-flow-scripts/flow/platforms/asap7/lib -name "*RVT_TT*.lib*" -printf " --liberty %p") --liberty /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_tt.lib --out /work/census.json' > "$OUT/census.log" 2>&1
