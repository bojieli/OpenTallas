#!/usr/bin/env bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/s81-svc8-1020
O=$R/out_codex_mapped_probe2
C=/srv/opentallas-scratch/claude/codex-svc7-hgrp-1020/out_graph2/verify_canonical/formal_prep
mkdir -p "$O"
cp "$R/out_codex_predecode_native/map/flat.v" "$O/gold.v"
cp "$R/out_codex_predecode_resume2/retained/mapped.v" "$O/cand.v"
cp "$C/library_model_formal.v" "$O/cells.v"
cp "$C/canonical_model_identity.json" "$O/canonical_model_identity.json"
cp "$R/src_codex_predecode/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v" "$O/memory.v"
cp "$R/tb_svc8_mapped.sv" "$O/tb.v"
python3 - "$O" <<'PY'
from pathlib import Path
import hashlib,json,sys
p=Path(sys.argv[1]);j=json.load(open(p/'canonical_model_identity.json'))
assert hashlib.sha256((p/'cells.v').read_bytes()).hexdigest()==j['imported_model_sha256']=='8883a21d9557e9dc5e070cbb1cdb934529c06b324e84dc110d1e166f60ab611d'
assert j['checks']==544 and j['plain_dff_checks']==128
assert all(v['pass_canonical_coupon'] for v in j['imported_results'].values())
PY
sha256sum "$O"/{gold,cand,cells,memory,tb}.v "$O/canonical_model_identity.json" > "$O/source_identity.sha256"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version
"$VL" --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 500 --x-initial unique --x-assign unique --top-module tb_svc8_mapped -Mdir "$O/obj" -o sim "$O"/{gold,cand,cells,memory,tb}.v > "$O/build.log" 2>&1
for s in 1 2 3; do
 "$O/obj/sim" +seed=$s +verilator+rand+reset+2 +verilator+seed+$s > "$O/run_s$s.log" 2>&1
 tail -5 "$O/run_s$s.log"
done
