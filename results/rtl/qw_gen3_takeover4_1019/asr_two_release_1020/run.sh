#!/bin/bash
set -u
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version > verilator.version
python3 - <<'PY'
import hashlib
checks={'canonical_ASR_normalized.v':'ee63e9a38cab2a9fa507f6fdc0480b04f047088a2f76464a5fca6182a9ba26d5','canonical_DFF_normalized.v':'cbba1c176afe1a03e677d21ee4e095c7b3d326689d8ec5ec46640d3e43a26254'}
for f,h in checks.items():assert hashlib.sha256(open(f,'rb').read()).hexdigest()==h,(f,'MODEL_IDENTITY_FAIL')
print('CANONICAL_MODEL_HASHES_PASS')
PY
[ "$?" = 0 ] || exit 2
for m in 0 1 2 3 4 5 6 7; do
 "$VL" --binary --timing --x-initial unique --top-module tb -GMUT=$m -Wno-fatal --Mdir obj_m$m -j 2 tb.sv qfd_land8.sv canonical_ASR_normalized.v canonical_DFF_normalized.v > build_m$m.log 2>&1 || exit $?
 obj_m$m/Vtb +verilator+seed+1 > run_m$m.log 2>&1
 rc=$?
 if [ "$m" = 0 ]; then
  if [ "$rc" != 0 ]; then echo "GOLDEN_FAIL"; exit "$rc"; fi
  obj_m$m/Vtb +verilator+seed+37 > run_m0_seed37.log 2>&1 || exit $?
  echo "TWO_RELEASE_GOLDEN_PASS seeds1,37"
 else
  if [ "$rc" = 0 ]; then echo "UNCAUGHT_MUTANT $m"; exit 3; fi
  python3 - "$m" <<'PY'
import re,sys
m=sys.argv[1];t=open(f'run_m{m}.log').read();assert re.search(r'CHAIN_NATIVE_MISMATCH|FIRST_VALID_MISMATCH|ASYNC_CLEAR_FAIL|HELD_RELEASE_LEAK',t),('NO_CAUSAL_WITNESS',m)
PY
  [ "$?" = 0 ] || exit 4
  echo "TWO_RELEASE_MUTANT_$m CAUSAL_REJECT"
 fi
done
