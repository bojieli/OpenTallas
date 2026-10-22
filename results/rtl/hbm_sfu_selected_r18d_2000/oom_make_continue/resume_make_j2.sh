#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-sfu-selected-r18d-unroll-2000
obj="$r/out/obj"
# Preserve the actual terminated compilation transcript; resume generated C++ only.
test -f "$obj/Vtb_hgi_sfu_split_equiv.mk"
test -f "$r/out/build_oom143.log" || cp -p "$r/out/build.log" "$r/out/build_oom143.log"
make -C "$obj" -f Vtb_hgi_sfu_split_equiv.mk -j2 > "$obj/resume_make_j2.log" 2>&1
cd "$r/src"
python3 "$HOME/.local/opentallas-tools/verilator-5.050/share/ot_nba_guard/verilator_nba_guard.py" --json "$obj" > "$obj/resume_guard.json"
python3 - "$obj/resume_guard.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));assert not r['findings'],r['findings'];print('SELECTED_GUARD_PASS loops_checked=',r['loops_checked'],'findings=',len(r['findings']),flush=True)
PY
"$obj/Vtb_hgi_sfu_split_equiv" > "$r/out/run_resume.log" 2>&1
grep 'SFU_SPLIT_EQUIV PASS' "$r/out/run_resume.log"
grep 'PASS canonical Qswiglu' "$r/out/run_resume.log"
echo 'SELECTED_SFU_MAKE_J2_GATE PASS'
