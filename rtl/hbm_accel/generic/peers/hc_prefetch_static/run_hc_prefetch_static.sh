#!/bin/bash
# Run from frozen flat source directory containing all source files plus row.hex.
set -euo pipefail
out=${1:?output directory}; image=${2:?external row hex};mkdir -p "$out"
python3 - "$out" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);p.joinpath('source.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [*pathlib.Path('.').glob('*.sv'),*pathlib.Path('.').glob('*.v')]},indent=2)+'\n')
PY
for m in 0 1; do
  iverilog -g2012 -s tb_hgi_hc_prefetch_static -Ptb_hgi_hc_prefetch_static.MUT=$m -o "$out/m$m.vvp" *.sv *.v > "$out/m$m.compile.log" 2>&1
  set +e
  vvp "$out/m$m.vvp" +IMAGE="$image" > "$out/m$m.log" 2>&1
  rc=$?
  set -e
  cat "$out/m$m.log"
  if [[ $m == 0 ]]; then [[ $rc == 0 ]];grep 'HC_PREFETCH_STATIC PASS' "$out/m$m.log"
  else [[ $rc != 0 ]];grep 'actual aperture memory mismatch' "$out/m$m.log";fi
 done
