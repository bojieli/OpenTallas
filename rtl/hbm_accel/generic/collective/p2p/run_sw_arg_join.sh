#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory};INPUTS=${2:?native bank inputs}
mkdir -p "$OUT"
python3 "$ROOT/tools/hbm_coll_static/check_sw_arg_join.py" > "$OUT/parent_connections.json"
python3 - "$HERE/native_vm_sources.json" "$INPUTS" <<'PYVERIFY'
import hashlib,json,pathlib,sys
m=json.loads(pathlib.Path(sys.argv[1]).read_text());p=pathlib.Path(sys.argv[2])
for name,want in m['sha256'].items():
 if hashlib.sha256((p/name).read_bytes()).hexdigest()!=want:raise SystemExit('Native bank dependency changed:'+name)
PYVERIFY
for m in 0 1 2 3;do
 iverilog -g2012 -s tb_hgi_coll_sw_arg_join -Ptb_hgi_coll_sw_arg_join.MUT="$m" -o "$OUT/m$m.vvp" \
  "$HERE/tb_hgi_coll_sw_arg_join.sv" "$HERE/ot_hgi_coll_static_issuer.sv" "$HERE/ot_hfd_coll_q_static_v2.sv" \
  "$HERE/ot_hgi_coll_qslots.sv" "$HERE/ot_hgi_coll_argmax_static.sv" "$HERE/ot_hgi_coll_static_vmwrite.sv" \
  "$ROOT/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv" "$INPUTS/ot_vms_bank_static.sv" \
  "$INPUTS/ot_sram_1r1w_1024x256_m2_r2c2.v" \
  "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
  > "$OUT/m$m.compile.log" 2>&1 || { cat "$OUT/m$m.compile.log";exit 2; }
 if vvp "$OUT/m$m.vvp" > "$OUT/m$m.log" 2>&1;then
  cat "$OUT/m$m.log";[[ "$m" == 0 ]] || { echo mutant survived;exit 1; }
  grep -q '^SW_ARG_NATIVE_JOIN PASS' "$OUT/m$m.log"
 else
  cat "$OUT/m$m.log";[[ "$m" != 0 ]] || exit 1
  grep -q 'FATAL:' "$OUT/m$m.log";echo "SW ARG native join mutant$m rejected"
 fi
 rm "$OUT/m$m.vvp"
done
