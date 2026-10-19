#!/bin/bash
set -eu
OUT=$(realpath -m "$1");SIDE=$2;SRC=$(realpath "$3");R=$(cd "$(dirname "$0")/../../.." && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
python3 - "$R" "$SIDE" "$SRC" "$OUT" <<'PY'
from pathlib import Path
import json,hashlib,sys
r,side,src,out=sys.argv[1:];r,src,out=map(Path,(r,src,out))
j=json.loads((r/'results/rtl/sysface_ovl_safe_phase_1019/receipt.json').read_text())['profiles'][side]
for p,h in j['source_hashes'].items():assert hashlib.sha256((src/p).read_bytes()).hexdigest()==h,p
(out/'sources.f').write_text('\n'.join(str(src/p)for p in j['source_hashes'])+'\n')
PY
"$V" --version > "$OUT/verilator.txt";grep -q 5.050 "$OUT/verilator.txt"
for cfg in rx0 rx1 tx0;do
 tx=0;m=0;[ "$cfg" != tx0 ] || tx=1;[ "$cfg" != rx1 ] || m=1
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -DOT_MEM_NO_INIT --top-module "tb_${SIDE}_ovl_phase" -GTXPROBE=$tx -GMUT=$m --Mdir "$OUT/obj_$cfg" -f "$OUT/sources.f" > "$OUT/build_$cfg.log" 2>&1
 "$OUT/obj_$cfg/Vtb_${SIDE}_ovl_phase" > "$OUT/run_$cfg.log" 2>&1
 cat "$OUT/run_$cfg.log";grep -q PHASE_PASS "$OUT/run_$cfg.log"
done
