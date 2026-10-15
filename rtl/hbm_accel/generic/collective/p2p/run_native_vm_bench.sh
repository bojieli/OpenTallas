#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=${1:?output directory}
INPUTS=${2:?source-pinned native bank and macro directory}
python3 - "$HERE/native_vm_sources.json" "$INPUTS" <<'PYVERIFY'
import hashlib,json,pathlib,sys
manifest=json.loads(pathlib.Path(sys.argv[1]).read_text());inputs=pathlib.Path(sys.argv[2])
for name,want in manifest['sha256'].items():
 if hashlib.sha256((inputs/name).read_bytes()).hexdigest()!=want:
  raise SystemExit('Native VM dependency changed: '+name)
PYVERIFY
mkdir -p "$OUT"
for shape in 5:1 7:3;do
 rg=${shape%:*};wg=${shape#*:}
 for mutant in 0 1 2 3 4;do
  stem="rg${rg}_wg${wg}_mut${mutant}"
  iverilog -g2012 -s tb_hgi_coll_native_vm -Ptb_hgi_coll_native_vm.RG="$rg" \
   -Ptb_hgi_coll_native_vm.WG="$wg" -Ptb_hgi_coll_native_vm.MUT="$mutant" -o "$OUT/$stem.vvp" \
   "$HERE/tb_hgi_coll_native_vm.sv" "$HERE/ot_hgi_coll_static_vmwrite.sv" \
   "$HERE/ot_hfd_coll_q_static.sv" "$HERE/ot_hgi_coll_qslots.sv" \
   "$INPUTS/ot_vms_bank_static.sv" "$INPUTS/ot_sram_1r1w_1024x256_m2_r2c2.v" > "$OUT/$stem.compile.log" 2>&1
  if vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1;then
   cat "$OUT/$stem.log"
   [[ "$mutant" == 0 ]] || { echo "mutant survived";exit 1; }
   grep -q '^HCOLL_NATIVE_VM PASS' "$OUT/$stem.log"
  else
   cat "$OUT/$stem.log"
   [[ "$mutant" != 0 ]] || exit 1
   grep -q 'FATAL:' "$OUT/$stem.log"
   echo "native VM mutant $mutant rejected as required"
  fi
  rm "$OUT/$stem.vvp"
 done
done
