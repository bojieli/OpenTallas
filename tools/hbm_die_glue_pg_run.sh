#!/bin/bash
set -eu
D=${D:-/srv/opentallas-scratch/claude/hbmdie-v10}
W=$D/pg_1013/glue
ot-heavy --mem 8 -- docker run --rm --name hbm_native_glue_pg --cpus=8 --memory=8g -v "$W:/work" openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 - <<"PYV"
import gzip,hashlib,json,re
from pathlib import Path
b=Path("/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM")
p=b/"asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
f=b/"asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz"
s=p.read_text();t=gzip.decompress(f.read_bytes()).decode()
def body(t,name): return t.split("cell ("+name+")",1)[1].split("  cell (",1)[0]
ff=body(s,"DFFHQNx1_ASAP7_75t_R");inv=body(t,"INVx2_ASAP7_75t_R");buf=body(t,"BUFx24_ASAP7_75t_R")
assert "next_state : \"!D\"" in ff and "function : \"IQN\"" in ff
assert any(x.replace("(","").replace(")","")=="!A" for x in re.findall(r"function : \"(.*?)\"",inv))
assert any(x.replace("(","").replace(")","")=="A" for x in re.findall(r"function : \"(.*?)\"",buf))
j=dict(verified=True,ff_QN="registered(!D)",reset_output="INV(QN) = registered(D)",clock_buffer="Y=A",liberty_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (p,f)})
Path("/work/cell_truth.json").write_text(json.dumps(j,indent=2)+"\n")
PYV
rc=$?; if [ $rc -eq 0 ]; then openroad -threads 8 -no_init -exit /work/run.tcl > /work/run.log 2>&1; rc=$?; fi
echo $rc > /work/run.exit
chmod -R a+rwX /work
exit $rc
'
