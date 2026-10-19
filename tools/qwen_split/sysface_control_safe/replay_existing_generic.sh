#!/bin/bash
# Re-read completed immutable generic JSON. Never starts synthesis or overwrites it.
set -eu
frozen=$1
out=$2
mkdir -p "$out"
for p in cold legacy; do
 test -s "$frozen/$p/roundtrip.json" || { echo "NOT_READY $p/roundtrip.json"; exit 75; }
 python3 tools/qwen_split/sysface_control_safe/check_emitted.py --top qfd_sys_face_control_safe__safe_core "$frozen/$p/generated/graph.json" "$frozen/$p/roundtrip.json" --source "$frozen/$p/generated/parent.sv" --out "$out/${p}_emitted.json"
 python3 tools/qwen_split/sysface_control_safe/check_physical_wrapper.py "$frozen/$p/original.json" "$frozen/$p/roundtrip.json" "$frozen/$p/generated/receipt.json" --out "$out/${p}_wrapper.json"
done
