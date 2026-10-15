#!/usr/bin/env bash
set -euo pipefail
p=$(cd -- "$(dirname -- "$0")" && pwd)
out=${1:?output directory};inputs=${2:?native selector staging and macro sources};vectors=${3:?declared input vectors}
mkdir -p "$out"
python3 - "$p/idx_tkm_native_sources.json" "$inputs" <<'PYVERIFY'
import hashlib,json,pathlib,sys
m=json.loads(pathlib.Path(sys.argv[1]).read_text());p=pathlib.Path(sys.argv[2])
for name,want in m['input_SHA256'].items():
 if hashlib.sha256((p/name).read_bytes()).hexdigest()!=want:raise SystemExit('Native INDEX dependency changed:'+name)
PYVERIFY
for m in 0 1 2 3;do
 iverilog -g2012 -s tb_hgi_coll_idx_transport -Ptb_hgi_coll_idx_transport.MUT="$m" -o "$out/m$m.vvp" \
  "$p/tb_hgi_coll_idx_transport.sv" "$p/ot_hgi_coll_vm_idx_ingress.sv" "$p/ot_hgi_coll_qslots.sv" \
  "$inputs/ot_hbm_idx_selector_static.sv" "$inputs/ot_hbm_idx_topk_link_static.sv" \
  "$inputs/ot_sram_1r1w_64x512_m1_r2c2.v" "$inputs/ot_sram_1r1w_256x256_m2_r2c2.v" > "$out/m$m.compile.log" 2>&1 || { cat "$out/m$m.compile.log";exit 2; }
 if (cd "$vectors"&&vvp "$out/m$m.vvp") > "$out/m$m.log" 2>&1;then
  cat "$out/m$m.log";[[ "$m" == 0 ]] || { echo mutant survived;exit 1; }
  grep -q '^IDX_NATIVE_TRANSPORT PASS' "$out/m$m.log"
 else
  cat "$out/m$m.log";[[ "$m" != 0 ]] || exit 1
  grep -q 'FATAL:' "$out/m$m.log";echo "native INDEX transport mutant$m rejected"
 fi
 rm "$out/m$m.vvp"
done
