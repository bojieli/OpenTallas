#!/bin/bash
set -euo pipefail
R=$PWD
export QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64 HDC_KV_FMT=fp8
export OT_GOLD_ROOT="$R/src"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p fx runs
verilator --version
for layer in 0 1; do
  python3 src/tools/qwen_layerbench/dv_layer_fixture.py tp8stages \
    --img "$R/img/L{layer}/die{die}" --tp8gold "$R/gold/P8191/P8191" \
    --layer "$layer" --out "$R/fx"
done
python3 - <<'PY'
import hashlib,json
from pathlib import Path
r=Path.cwd()
files=[r/'bin/Vtb',r/'src/tools/qwen_layerbench/dv_layer_fixture.py',r/'run_tp8_stages.sh']
record={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(r/'source_receipt.json').write_text(json.dumps(dict(source_commit='9f185989e',
    binary='Reused immutable Verilator5.050 N12/MUT0/MU_NU1 odscale executable; no rebuild',
    scope='Native TP8 recorded L0/L1 component operands; no full-token or new SAFE RTL claim',
    sha256=record),indent=1)+'\n')
PY
job() {
  name=$1; shift
  d="$R/runs/$name"
  mkdir -p "$d"
  ln -s "$R/bin" "$d/obj_n12"
  set +e
  python3 "$@" --work "$d" >"$d/bench.out" 2>&1
  rc=$?
  set -e
  echo "rc=$rc" >>"$d/bench.out"
  head -1 "$d/bench.out"
}
export R
export -f job
{
  for layer in 0 1; do
    echo "L${layer}_resid1 src/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode resid --ar-order row --fixture $R/fx/L${layer}_resid1_tp8.npz"
    echo "L${layer}_silu src/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode silu --fixture $R/fx/L${layer}_silu_tp8.npz"
    echo "L${layer}_qkv src/rtl/test/qwen_dv/dv_lower_mat_bench.py --run qkv --fixture $R/fx/L${layer}_mat_qkv_tp8.npz"
    echo "L${layer}_gu src/rtl/test/qwen_dv/dv_lower_mat_bench.py --run gu --fixture $R/fx/L${layer}_mat_gu_tp8.npz"
  done
  echo "L0_resid2 src/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode resid --ar-order row --fixture $R/fx/L0_resid2_tp8.npz"
  echo "MUT_L0_resid1_nor src/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode resid --ar-order row --mutant nor --fixture $R/fx/L0_resid1_tp8.npz"
  echo "MUT_L0_silu_nor src/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode silu --mutant nor --fixture $R/fx/L0_silu_tp8.npz"
} | xargs -P4 -L1 bash -c 'job "$@"' _
