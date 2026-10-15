#!/usr/bin/env bash
# Reuse an already built native arithmetic service; never rebuild the 107GB
# hierarchical model merely to link its component test. Run through ot-run.
# Usage: script <RTL library build> <vector directory> <fresh result directory>
set -euo pipefail
build=$(realpath "${1:?RTL library build}")
vectors=$(realpath "${2:?vectors}")
out=$(realpath -m "${3:?fresh output directory}")
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/.." && pwd)
[[ ! -e "$out" ]] || { echo 'Output must be fresh' >&2; exit 2; }
mkdir -p "$out"
python3 "$here/qwen_composed_harness/attention_rtl_library_check.py" "$build" > "$out/arithmetic-provenance.json"
vroot=${VERILATOR_ROOT:-$HOME/.local/opentallas-tools/verilator-5.050/share/verilator}
g++ -O1 -std=c++20 -pthread -I"$build/obj" -I"$vroot/include" -I"$vroot/include/vltstd" \
 "$root/rtl/test/nearhbm/tb_qwen_tp8_attention_service.cpp" \
 "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" \
 "$build/libot_qwen_tp8_attention_service.so" -Wl,-rpath,"$build" -o "$out/check" > "$out/link.log" 2>&1
sha256sum "$out/check" "$root/rtl/test/nearhbm/tb_qwen_tp8_attention_service.cpp" "$build/libot_qwen_tp8_attention_service.so" > "$out/inputs.sha256"
# Golden values are comparison-only; Q and KV are declared component inputs.
# These are arithmetic/component tests, not integrated on-chip memory proof.
for mode in steady coldboot idle q_order k_epoch k_order v_epoch capability context precision; do
 "$out/check" "$vectors" "$mode" > "$out/$mode.json" 2> "$out/$mode.err"
done
python3 - "$out" <<'PY'
import json
from pathlib import Path
import sys
p = Path(sys.argv[1])
rows = {f.stem: json.loads(f.read_text()) for f in p.glob('*.json') if f.stem != 'arithmetic-provenance'}
for mode in ('steady', 'coldboot', 'idle'):
    assert rows[mode]['exact'], rows[mode]
for mode in ('q_order', 'k_epoch', 'k_order', 'v_epoch', 'capability', 'context', 'precision'):
    assert rows[mode]['fault'] or rows[mode]['data_errors'], rows[mode]
summary = {'scope': 'RTL_ATTENTION_ARITHMETIC_COMPONENT_ONLY', 'status': 'PASS',
           'cases': rows, 'full_native_token_qualified': False,
           'static_production_schedule_qualified': False}
(p / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
PY
