#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TASK_OUT=${OUT:?OUT must name a fresh evidence directory}
TASK_SRC=${CORE_SOURCE_DIR:?CORE_SOURCE_DIR must contain pinned source_manifest.json}
TASK_VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[[ -x "$TASK_VERILATOR" ]] || TASK_VERILATOR=verilator
mkdir -p "$TASK_OUT"
python3 - "$TASK_SRC" "$TASK_OUT" <<'PY'
import json,hashlib,sys,pathlib
src,out=map(pathlib.Path,sys.argv[1:]);m=json.loads((src/'source_manifest.json').read_text())
for e in m['files']:
 p=src/pathlib.Path(e['path']).name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],p
assert 'FIN_BYPASS==2' in (src/'ot_hgi_qdq_core_fin2.sv').read_text()
(out/'source_manifest.json').write_text(json.dumps(m,indent=2)+'\n')
PY
"$TASK_VERILATOR" --binary --timing -Wno-fatal -j 4 --top-module tb_hgi_qdq_core_fin2_oracle \
 -GMUT_CAND="${MUT_CAND:-0}" -GCORE_SPANPIPE="${CORE_SPANPIPE:-1}" -GFR_SPANPIPE="${FR_SPANPIPE:-1}" --Mdir "$TASK_OUT/obj" \
 "$TASK_SRC/ot_rst_relay.sv" "$TASK_SRC/ot_hgi_quant_record.sv" "$TASK_SRC/ot_hgi_qdq_fr.sv" \
 "$TASK_SRC/ot_hgi_qdq_core.sv" "$TASK_SRC/ot_hgi_qdq_core_fin2.sv" \
 "$TASK_ROOT/rtl/test/hbm_accel/generic/tb_hgi_qdq_core_fin2_oracle.sv" > "$TASK_OUT/build.log" 2>&1
set +e
"$TASK_OUT/obj/Vtb_hgi_qdq_core_fin2_oracle" > "$TASK_OUT/sim.log" 2>&1
TASK_RC=$?
set -e
cat "$TASK_OUT/sim.log"
exit "$TASK_RC"
