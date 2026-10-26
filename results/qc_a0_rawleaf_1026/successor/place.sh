#!/bin/bash
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus=8 --memory=40g --memory-swap=40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
P=/OpenROAD-flow-scripts/flow/platforms/asap7
yosys -Q -p "read_liberty -ignore_miss_func $P/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz; read_verilog /work/exact.v; hierarchy -top miter; flatten; proc; opt; sat -seq 4 -set-init-zero -prove bad 0 -verify" > /work/exact.log 2>&1
if yosys -Q -p "read_liberty -ignore_miss_func $P/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz; read_verilog /work/mutant.v; hierarchy -top miter; flatten; proc; opt; sat -seq 4 -set-init-zero -prove bad 0 -verify" > /work/mutant.log 2>&1; then
 echo "ERROR mutant escaped"; exit 1
fi
grep -q "proof did fail" /work/mutant.log
echo "ADDER_EXPANSION_LOCKSTEP PASS 4 sequential steps, exhaustive inputs; inverted-SN mutant caught"
# The source is a physical mapped cut. RTL lint must read the physical cell
# declarations; keep the standard libraries local to this standalone kit.
mkdir -p /work/macros
cp "$P"/lib/NLDM/*RVT_TT*.lib* /work/macros/
python3 -I /work/rtl_lint.py /work
python3 -I /work/sdc_lint.py /work
python3 -I /work/adder_map_dontuse.py gen --platform-dir "$P" --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run NUM_CORES=8 /work/run/results/asap7/lsl_rawfault_m3/base/1_2_yosys.v
python3 -I /work/adder_map_dontuse.py check --platform-dir "$P" --netlist /work/run/results/asap7/lsl_rawfault_m3/base/1_2_yosys.v --report /work/dont_use_check.json
python3 - <<"PY"
import re,json
from pathlib import Path
p=Path("/work/run/results/asap7/lsl_rawfault_m3/base/1_2_yosys.v")
s=p.read_text(); cells=re.findall(r"^\s*([A-Za-z][A-Za-z0-9_]*_ASAP7_\w+)\s+",s,re.M)
ff=[x for x in cells if x.startswith("DFF")]
r={"cells":len(cells),"ff":len(ff),"cap":400000,"HAxp5":sum(c.startswith("HAxp5") for c in cells)}
print("SIZE_GATE",r)
assert 0<len(cells)<=400000,r
assert len(ff)==12030,r
assert r["HAxp5"]==0,r
Path("/work/size_gate.json").write_text(json.dumps(r,indent=2))
PY
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run NUM_CORES=8 place
' > "$K/place.log" 2>&1
