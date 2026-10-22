#!/bin/bash
set -uo pipefail
OUT=$(mkdir -p "$1"&&realpath "$1")
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
python3 - "$OUT" <<'PYMODEL'
from pathlib import Path
import sys,hashlib,json
src=Path('rtl/physical/qcluster/qfd_c_land_safe.sv').read_text()
model=src.replace('qfd_c_land_','qfd_c_land_model_').replace('if(W>258)','if(W>516)').replace('if(W>258 ||','if(W>516 ||')
p=Path(sys.argv[1]);(p/'model_full.sv').write_text(model)
(p/'model_sources.json').write_text(json.dumps(dict(production_sha256=hashlib.sha256(src.encode()).hexdigest(),model_sha256=hashlib.sha256(model.encode()).hexdigest(),changes='module namespace and simulation-only width guard258->516; no full physical/adoption waiver'),indent=1)+'\n')
PYMODEL
err=0
for C in 514:0 516:0 516:1;do
 W=${C%:*};M=${C#*:}
 "$V" --binary --timing -j 8 -Wno-fatal --top-module tb -GW=$W -GMUT=$M -Mdir "$OUT/obj${W}m$M" rtl/physical/qcluster/qfd_c_land.sv rtl/physical/qcluster/qfd_c_land_safe.sv "$OUT/model_full.sv" rtl/test/tb_qfd_c_full_land_model.sv > "$OUT/build${W}m$M.log" 2>&1||{ err=1;continue; }
 if [[ $M == 0 ]];then phases="-4 0 4";else phases="0";fi
 for P in $phases;do
  "$OUT/obj${W}m$M/Vtb" +PHASE=$P > "$OUT/w${W}m${M}p$P.log" 2>&1
  if [[ $M == 0 ]];then grep -q "FULL_LAND_PASS W$W MUT0 PHASE$P" "$OUT/w${W}m${M}p$P.log"||err=1
  else grep -q "FULL_LAND_FAIL W$W MUT1 PHASE$P" "$OUT/w${W}m${M}p$P.log"||err=1;fi
 done
done
echo "FULL_LAND_MODEL_EXIT $err"
exit "$err"
