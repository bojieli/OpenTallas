#!/usr/bin/env bash
# Full current SID-zero wrapper, all 2048 hslices, no blackboxes.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-client-sw-vl}"); mkdir -p "$out"
mapfile -t src < <(python3 - <<'PYSRC'
import re
s=open('rtl/test/hbm_idx_static/run_client_elab.sh').read()
a=re.search(r'src=\((.*?)\)',s,re.S).group(1).split()
a += ['rtl/hdc/ot_hdc_delay_rf.sv','rtl/hbm_accel/index/ot_hbm_idx_client_static_sw.sv']
print('\n'.join(dict.fromkeys(a)))
PYSRC
)
sha256sum "${src[@]}" > "$out/sources.sha256"
if test -f SOURCE_SHA256; then sha256sum -c SOURCE_SHA256 > "$out/staged_source_check.log"; fi
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
set +e
/usr/bin/time -v "$vl" --lint-only -Wall -Wno-fatal --top-module ot_hbm_idx_client_static_sw "${src[@]}" > "$out/vl.log" 2>&1
vrc=$?
set -e
printf '%s\n' "$vrc" > "$out/tool.status"
nerr=$(grep -c '^%Error' "$out/vl.log" || true)
npin=$(grep -cE '%Warning-(PINMISSING|PINNOTFOUND)' "$out/vl.log" || true)
echo "VL rc=$vrc errors=$nerr pin_missing_or_notfound=$npin"
grep 'Maximum resident' "$out/vl.log" || true
if test "$vrc" = 0 && test "$nerr" = 0 && test "$npin" = 0; then
 echo IDX_CLIENT_SW_ELAB_VERILATOR_PASS
 echo 0 > "$out/status"
else
 echo IDX_CLIENT_SW_ELAB_VERILATOR_FAIL
 echo 1 > "$out/status"; exit 1
fi
