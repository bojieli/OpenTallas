#!/usr/bin/env bash
set -euo pipefail
mkdir -p out
python3 - <<'PY'
import json,hashlib
for r in json.load(open('source_manifest.json')):assert hashlib.sha256(open(r['file'],'rb').read()).hexdigest()==r['sha256'],r['file']
PY
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version > out/tool_version.txt
"$VL" --binary --timing --x-initial unique --x-assign unique -Wno-fatal -j 8 -O1 --top-module tb_dma_integrated -Mdir out/obj -f sources.f > out/build.log 2>&1
sha256sum out/obj/Vtb_dma_integrated > out/binary.sha256
out/obj/Vtb_dma_integrated +verilator+rand+reset+2 > out/positive.log 2>&1
if out/obj/Vtb_dma_integrated +verilator+rand+reset+2 +MUTATE_BANK > out/mutant.log 2>&1;then echo MUTANT_UNEXPECTED_PASS;exit 4;fi
grep -Eq 'VM_FAULT|ROUTE_MISMATCH|READBACK' out/mutant.log
grep 'DMA_PRODUCER_INTEGRATED_PASS' out/positive.log

if out/obj/Vtb_dma_integrated +verilator+rand+reset+2 +MUTATE_HBM > out/hbm_mutant.log 2>&1;then echo HBM_MUTANT_UNEXPECTED_PASS;exit 5;fi
grep 'ROUTE_DATA' out/hbm_mutant.log
