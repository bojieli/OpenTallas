#!/usr/bin/env bash
# One source-identical compiler-method correction; one context, all controls share its ELF.
set -uo pipefail
BASE=/srv/opentallas-scratch2/claude/codex-qwen-root-native-1101
PACKET=$BASE/prep3
OUT=$BASE/run_inline1
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p "$OUT"
if test -e "$OUT/status"; then echo 'REFUSE: existing native ROOT run state'; exit 70; fi
cd "$PACKET"
printf 'START %s host=%s\n' "$(date -Is)" "$(hostname)" > "$OUT/status"
"$VL" --version > "$OUT/verilator_version.txt"
/usr/bin/time -v -o "$OUT/build.time" "$VL" --binary --timing -O0 -finline -j 1 \
 --output-split 10000 --output-split-cfuncs 1000 --x-assign 0 --x-initial 0 \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
 -CFLAGS '-O0 -w -fno-var-tracking' -f defines.f -f source.f \
 --top-module tb_native_root --Mdir "$OUT/obj" > "$OUT/build.log" 2>&1
build_rc=$?
printf 'BUILD_RC %s %s\n' "$build_rc" "$(date -Is)" >> "$OUT/status"
if test "$build_rc" -ne 0; then exit "$build_rc"; fi
sha256sum "$OUT/obj/Vtb_native_root" > "$OUT/binary.sha256"
for mode in nominal COLLECT_CFG LATE_CFG; do
 args=(); if test "$mode" != nominal; then args=(+"$mode"); fi
 /usr/bin/time -v -o "$OUT/$mode.time" "$OUT/obj/Vtb_native_root" "${args[@]}" > "$OUT/$mode.log" 2>&1
 rc=$?
 printf '%s\n' "$rc" > "$OUT/$mode.exit"
 printf 'RUN_RC %s %s %s\n' "$mode" "$rc" "$(date -Is)" >> "$OUT/status"
done
python3 - "$OUT" <<'PY'
import json,re,sys
from pathlib import Path
out=Path(sys.argv[1]);runs={}
for mode in ('nominal','COLLECT_CFG','LATE_CFG'):
 log=(out/(mode+'.log')).read_text();rc=int((out/(mode+'.exit')).read_text())
 runs[mode]=dict(exit=rc,pass_marker='NATIVE_ROOT_FOUR_CASES_PASS' in log,
                case_lines=[l for l in log.splitlines() if 'NATIVE_ROOT_CASE ' in l],
                lease_overlap_lines=[l for l in log.splitlines() if 'ROOT_CFG_DURING_LEASE' in l],
                assertion_lines=[l for l in log.splitlines() if any(x in l for x in ('$fatal','Error:','Assertion','ROOT_OUTPUT_ADDRESS','ROOT_RSTD_BITS','NO_NATIVE_RSTD','CFG_LEASE_CONTROL_NOT_CAUGHT'))])
nom=runs['nominal']['exit']==0 and runs['nominal']['pass_marker']
controls=all(runs[m]['exit']!=0 and runs[m]['lease_overlap_lines'] and
             any(any(k in l for k in ('ROOT_OUTPUT_ADDRESS','ROOT_RSTD_BITS','NO_NATIVE_RSTD','NATIVE_ROOT_FAULT')) for l in runs[m]['assertion_lines'])
             and not any('CFG_LEASE_CONTROL_NOT_CAUGHT' in l for l in runs[m]['assertion_lines']) for m in ('COLLECT_CFG','LATE_CFG'))
precision=[]
for p in (out/'obj').glob('*Syms*.cpp'):
 for l in p.read_text().splitlines():
  if 'timeprecision(' in l or 'timeunit(' in l:precision.append(l.strip())
result=dict(status='PASS_COMPONENT_ONLY' if nom and controls else 'FAIL_COMPONENT',
            runs=runs,compiled_context_time=precision,
            nominal_pass=nom,controls_caught=controls,
            scope='One native k79 ROOT arithmetic fixture; external PSUM inputs; no production lease/TREQ/HEAD closure')
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'], 'nominal',nom,'controls',bool(controls))
raise SystemExit(not(nom and controls))
PY
rc=$?
printf 'COMPLETE_RC %s %s\n' "$rc" "$(date -Is)" >> "$OUT/status"
exit "$rc"
