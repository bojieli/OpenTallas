#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
export VERILATOR="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
export PATH="$(dirname "$VERILATOR"):$PATH"
"$VERILATOR" --version
python3 - "$OUT" <<'INNER'
import json,subprocess,sys
j=json.load(open('physical/ref_tile/qfd_tile_nk_romleaf_rc15a/job.json'))
cmd=j['stages']['bench'][0]['cmd'].replace('{RUN}',sys.argv[1]+'/elab')
assert j['stages']['bench'][0]['name']=='lint'
subprocess.run(cmd,shell=True,check=True)
print('A0_RC15_PRODUCTION_ELAB_PASS',flush=True)
INNER
bash tools/qwen_romleaf/rc15_2000/parent_native_pinned.sh "$OUT/native" 0 > "$OUT/parent_native_PASS.log" 2>&1
set +e
bash tools/qwen_romleaf/rc15_2000/parent_native_pinned.sh "$OUT/native" 4 > "$OUT/parent_native_clock_MUT4_FAIL.log" 2>&1
mut_rc=$?
set -e
if [[ "$mut_rc" == 0 ]] || ! grep -Eq 'ROMLEAF_PARENT_NK_NATIVE_FAIL MUT4 errors[1-9]' "$OUT/parent_native_clock_MUT4_FAIL.log"; then
 cat "$OUT/parent_native_clock_MUT4_FAIL.log"
 echo A0_RC15_MUTANT_DID_NOT_FAIL
 exit 1
fi
grep -E '^ROMLEAF_PARENT_NK_NATIVE_PASS' "$OUT/parent_native_PASS.log"
grep -E 'ROMLEAF_PARENT_NK_NATIVE_FAIL MUT4' "$OUT/parent_native_clock_MUT4_FAIL.log"
echo A0_RC15_EXISTING_NATIVE_OBLIGATIONS_PASS
