#!/usr/bin/env bash
# Small two-plane programme component gate; run through ot-run. OUT/vec has
# serial/ and stream/ products of generic su_programme_compile.py.
set -euo pipefail
ulimit -c 0
cd "$(dirname "$0")/../.."
out=$(realpath "$1")
read -r NE PE < <(python3 - "$out/vec" <<'PY'
import json,sys
from pathlib import Path
v=Path(sys.argv[1]);print(json.loads((v/'serial/manifest.json').read_text())['edges'],json.loads((v/'stream/manifest.json').read_text())['edges'])
PY
)
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
s=rtl/hbm_accel/generic/adapters/static_su/programme
"$vl" --binary --timing -O1 -j 2 -Wno-fatal --top-module tb_hbm_su_multirate_programmes \
 -I"$out/vec" -GNE="$NE" -GPE="$PE" --Mdir "$out/obj" \
 "$s/ot_hbm_su_programme.sv" "$s/multirate_programmes_tb.sv" \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/build.log" 2>&1
"$out/obj/Vtb_hbm_su_multirate_programmes" +DIR="$out/vec" > "$out/positive.log" 2>&1
grep -q 'SU_MULTIRATE_PROGRAMMES PASS' "$out/positive.log"
for mut in SERIAL STREAM SHIFT;do
 set +e
 "$out/obj/Vtb_hbm_su_multirate_programmes" +DIR="$out/vec" +MUT_$mut > "$out/mut_$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q 'SU_MULTIRATE_PROGRAMMES FAIL' "$out/mut_$mut.log";then exit 1;fi
done
echo SU_MULTIRATE_PROGRAMMES_GATE_PASS
