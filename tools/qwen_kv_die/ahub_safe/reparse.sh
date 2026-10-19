#!/bin/bash
set -euo pipefail
B=$(realpath ..)
docker run --rm -v "$B:/run" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -p "read_json /run/synth/safe2.mapped.json; read_verilog /run/distributed/qkd_ahub_static_dw_safe_native.v; hierarchy -check -top qkd_ahub_static_dw_safe_native; synth -top qkd_ahub_static_dw_safe_native -flatten; check -assert; write_json /run/distributed/reparsed.json"'
python3 tools/qwen_kv_die/ahub_safe/verify.py "$B/synth/safe2.mapped.json" "$B/distributed/reparsed.json" "$B/distributed/distribution.json" > "$B/distributed/verification.json"
cat "$B/distributed/verification.json"
