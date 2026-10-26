#!/bin/bash
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus=8 --memory=40g --memory-swap=40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run_ffpg NUM_CORES=8 /work/run_ffpg/results/asap7/lsl_rawfault_m3/base/1_2_yosys.v
python3 - <<"PY"
import re,json
from pathlib import Path
p=Path("/work/run_ffpg/results/asap7/lsl_rawfault_m3/base/1_2_yosys.v")
s=p.read_text(); cells=re.findall(r"^\s*([A-Za-z][A-Za-z0-9_]*_ASAP7_\w+)\s+",s,re.M)
ff=[x for x in cells if x.startswith("DFF")]
r={"cells":len(cells),"ff":len(ff),"cap":400000}; print("SIZE_GATE",r)
assert 50000<len(cells)<=400000,r
assert len(ff)==12030,r
Path("/work/size_gate.json").write_text(json.dumps(r,indent=2))
PY
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run_ffpg NUM_CORES=8 place' > "$K/place.log" 2>&1
