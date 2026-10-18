#!/bin/bash
# KVJ-B 2026-10-17: lockstep gate of qkd_attn_service_root vs the verbatim w16 fixed calendar control.
# Usage: run_service_root_lockstep.sh OUT_DIR [N_EDGES]   (run from a checkout; writes OUT_DIR/receipt.json)
# PASS needs: generated files current (mk_service_root.py --check), LEAD 0 and LEAD 2 exact over 2 seeds each, and
# every mutant (MUT 1 start_pv late, MUT 2 ctx off by one; LEAD 0 and 2) mismatching.
set -euo pipefail
R=$(git rev-parse --show-toplevel); O=$(realpath -m "$1"); N=${2:-2000000}; mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 "$R/tools/qwen_attention_native/mk_service_root.py" --check
python3 - "$R" "$O/cals.hex" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + '/tools/qwen_attention_native')
import attn_calendar as a
Ts = [1, 2, 7, 100, 127, 128, 129, 255, 256, 257, 511, 512, 513, 1000, 1024, 2048, 3000, 4096, 5000, 6144, 7000, 8000, 8191, 8192]
open(sys.argv[2], 'w').write(''.join(a.hexcal(a.calendar_w16(T, head_g3s2=g)) + '\n' for T in Ts for g in (False, True)))
PY
SRC=("$R/rtl/qwen_sys/split_20261014/qkd_attn_service_root.sv" "$R/rtl/test/qwen_split/qkd_attn_service_root_ref.sv"
     "$R/rtl/test/qwen_split/tb_qkd_attn_service_root_lockstep.sv")
CFG="0:0 2:0 0:1 0:2 2:1 2:2"
for c in $CFG; do L=${c%:*}; M=${c#*:}
 ( "$VL" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_qkd_attn_service_root_lockstep \
   -GLEAD=$L -GMUT=$M --Mdir "$O/b_L${L}_M${M}" "${SRC[@]}" > "$O/b_L${L}_M${M}.build.log" 2>&1 ) & done; wait
for c in $CFG; do L=${c%:*}; M=${c#*:}; for s in 1 2; do
 ( "$O/b_L${L}_M${M}/Vtb_qkd_attn_service_root_lockstep" +N=$N +SEED=$s +CALS="$O/cals.hex" > "$O/L${L}_M${M}_s$s.log" 2>&1 ) &
done; done; wait
python3 - "$O" "$R" "$CFG" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
O, R, cfg = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3].split()
runs, ok = [], True
for c in cfg:
    L, M = map(int, c.split(':'))
    for s in (1, 2):
        t = (O / f'L{L}_M{M}_s{s}.log').read_text()
        line = next((l for l in t.splitlines() if l.startswith('LOCKSTEP PASS') or l.startswith('LOCKSTEP FAIL')), 'NO_RESULT')
        passed = line.startswith('LOCKSTEP PASS')
        want = M == 0
        ok &= passed == want
        runs.append(dict(lead=L, mut=M, seed=s, expect='PASS' if want else 'FAIL', result=line))
src = ['rtl/qwen_sys/split_20261014/qkd_attn_service_root.sv', 'rtl/test/qwen_split/qkd_attn_service_root_ref.sv',
       'rtl/test/qwen_split/tb_qkd_attn_service_root_lockstep.sv', 'rtl/hdc/nearhbm/ot_qwen_tp8_attention_native_service_w16.sv',
       'rtl/hdc/nearhbm/ot_qwen_tp8_attention_native_service_w16_sr.sv', 'tools/qwen_attention_native/mk_service_root.py',
       'tools/qwen_attention_native/run_service_root_lockstep.sh', 'tools/qwen_attention_native/attn_calendar.py']
rec = dict(schema='opentallas.kvjb.service_root_lockstep.v1', verdict='PASS' if ok else 'FAIL',
           commit=subprocess.run(['git', '-C', str(R), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
           dirty=bool(subprocess.run(['git', '-C', str(R), 'status', '--porcelain', '--', *src], capture_output=True, text=True).stdout.strip()),
           sources={p: hashlib.sha256((R / p).read_bytes()).hexdigest() for p in src},
           scope='qkd_attn_service_root (+ PV_LEAD relay) vs the verbatim fixed calendar control of the w16 service; '
                 'the rest of the _sr service is the canonical text (mk_service_root.py exact-match edits)',
           runs=runs)
(O / 'receipt.json').write_text(json.dumps(rec, indent=1) + '\n')
print(rec['verdict']); [print(r['lead'], r['mut'], r['seed'], r['expect'], r['result']) for r in runs]
sys.exit(0 if ok else 1)
PY
