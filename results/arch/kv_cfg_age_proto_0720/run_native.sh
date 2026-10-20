#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/codex-kv-cfg-age-proto-0720
mkdir -p "$base/native"
docker run --rm --cpus=2 --memory=16g -v "$base":/work -w /work openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
mkdir -p native/libs
cp "$L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" native/libs/SEQ.lib
for f in AO_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122 OA_RVT_TT_nldm_211120 SIMPLE_RVT_TT_nldm_211120;do zcat "$L/asap7sc7p5t_$f.lib.gz" > "native/libs/$f.lib";done
python3 - <<"PY"
from pathlib import Path
import re,hashlib,json
files=sorted(Path("native/libs").glob("*.lib"));txt="".join(p.read_text() for p in files);libs=re.split(r"(?m)^library\s*\(",txt);head="library ("+libs[1].split("cell (",1)[0];cells=[]
for lib in libs[1:]:
 body="cell ("+lib.split("cell (",1)[1];cells.append(body[:body.rstrip().rfind("}")])
Path("native/all.lib").write_text(head+"\n".join(cells)+"\n}\n")
Path("native/liberty_identity.json").write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+"\n")
PY
cat > native/probe.ys <<"YS"
read_liberty -lib native/all.lib
read_verilog -sv qkd_kv_die_cfg_a_s32_age.sv
chparam -set NRST 43 -set CAP 1 -set AGES 1 -set S32 1 qkd_kv_die_cfg_a_s32_age
hierarchy -check -top qkd_kv_die_cfg_a_s32_age
synth -top qkd_kv_die_cfg_a_s32_age -flatten -noabc
dfflibmap -liberty native/libs/SEQ.lib
abc -liberty native/all.lib
opt_clean
tee -o native/mapped.stat stat -liberty native/all.lib
write_verilog -noattr native/mapped.v
write_json native/mapped.json
YS
yosys -Q -l native/synth.log -s native/probe.ys > native/synth.stdout 2>&1
args=();for f in native/libs/*.lib;do args+=(--liberty "$f");done
python3 native_tools/tools/ref_tile/native_census.py --netlist native/mapped.v --top qkd_kv_die_cfg_a_s32_age "${args[@]}" --out native/native_census.json > native/native_census.stdout 2>&1 || echo "$?" > native/native_census.rc
' > "$base/native/driver.log" 2>&1
