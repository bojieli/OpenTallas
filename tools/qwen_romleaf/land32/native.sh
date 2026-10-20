#!/bin/bash
set -euo pipefail
mkdir -p native3
sed 's@native/mapped.v@native3/mapped.v@g' tools/qwen_romleaf/land32/native.ys > native3/map.ys
docker run --rm -v "$PWD:/work" -w /work --entrypoint yosys openroad/orfs:latest -s native3/map.ys > native3/map.log 2>&1
python3 tools/ref_tile/native_census.py --netlist native3/mapped.v --top land32_native --liberty native/AO.lib --liberty native/INVBUF.lib --liberty native/OA.lib --liberty native/SIMPLE.lib --liberty native/SEQ.lib --out native3/census.json > native3/census.log 2>&1
