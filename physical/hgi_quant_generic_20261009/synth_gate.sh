#!/bin/bash
# Admitted remote-only synthesis and strict boundary gate. No elapsed-time limits.
set -euo pipefail
src=$(realpath "$1"); out=$(realpath -m "$2")
mkdir -p "$out"
cd "$src"
source physical/qwen_die_masters/cfg/hgi_quant_pd50.env
printf '%s\n' "$(cat SOURCE_COMMIT)" > "$out/SOURCE_COMMIT"
python3 - "$SRCS" "$out" <<'PY'
import hashlib,json,sys
from pathlib import Path
srcs=sys.argv[1].split();out=Path(sys.argv[2])
(out/'source_sha256.json').write_text(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in srcs},indent=2)+'\n')
(out/'boundary.ys').write_text('read_verilog -sv -DSYNTHESIS '+ ' '.join(srcs)+'; hierarchy -check -top ot_hgi_quant_decode; proc; flatten; opt_clean; techmap; opt_clean; write_json '+str(out/'boundary.json')+'\n')
(out/'config.mk').write_text('export PLATFORM = asap7\nexport DESIGN_NAME = ot_hgi_quant_decode\nexport VERILOG_FILES = '+ ' '.join('/src/'+p for p in srcs)+'\nexport SDC_FILE = /src/physical/qwen_die_masters/die_p770.sdc\nexport DIE_AREA = 0 0 1800 600\nexport CORE_AREA = 2.16 2.16 1797.84 597.84\nexport PLACE_DENSITY = 0.50\nexport ADDER_MAP_FILE =\nexport NUM_CORES = 12\nexport SYNTH_HIERARCHICAL = 0\nexport SYNTH_MEMORY_MAX_BITS = 999999999\n')
PY
/usr/bin/time -v /home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys -s "$out/boundary.ys" > "$out/boundary.log" 2>&1
python3 - "$out" <<'PY'
import importlib.util,json,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('rb','tools/closure_loop/rtl_boundary.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
o=Path(sys.argv[1]);r=m._verdict(m.analyse(json.loads((o/'boundary.json').read_text()),'ot_hgi_quant_decode'),{'top':'ot_hgi_quant_decode'},16,True)
(o/'boundary_result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));assert r['verdict']=='PASS',r
PY
/usr/bin/time -v docker run --rm --user "$(id -u):$(id -g)" -v "$src:/src:ro" -v "$out:/out" --entrypoint bash openroad/orfs:asap7lock -lc 'cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/out/config.mk WORK_HOME=/out RESULTS_DIR=/out/results LOG_DIR=/out/logs REPORTS_DIR=/out/reports OBJECTS_DIR=/out/objects NUM_CORES=12 synth' > "$out/synth.log" 2>&1
