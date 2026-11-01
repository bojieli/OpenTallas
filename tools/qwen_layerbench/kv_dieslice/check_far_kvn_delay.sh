#!/bin/bash
# Small KV-FN integration vehicle: exact relay depths, production transport + master codec.
# E3=2 is the seeded one-cycle-late control; E3=1 must fill all four scheduled slots.
set -euo pipefail
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
OUT=${1:?usage: check_far_kvn_delay.sh SCRATCH_OUTPUT_DIR}
mkdir -p "$OUT"
python3 - "$ROOT" "$OUT" <<'PY'
from pathlib import Path
import sys
root,out=map(Path,sys.argv[1:])
for rel,mod in [('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv','ot_qwen_d2d_kvn_tx'),('tools/qwen_layerbench/kv_dieslice/kvs_compute_end.sv','kvs_dly')]:
 text=(root/rel).read_text(); text=text[text.index('module '+mod):]; text=text[:text.index('endmodule')+len('endmodule')]
 (out/(mod+'.sv')).write_text(text)
PY
"${IVERILOG:-iverilog}" -g2012 -s tb -o "$OUT/e3micro" "$OUT/ot_qwen_d2d_kvn_tx.sv" "$ROOT/rtl/qwen_split/qfd_kvn_static_transport.sv" "$OUT/kvs_dly.sv" "$ROOT/tools/qwen_layerbench/kv_dieslice/tb_far_kvn_delay.sv"
"${VVP:-vvp}" "$OUT/e3micro"
