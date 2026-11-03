#!/bin/bash
set -euo pipefail
ulimit -c 0
R=/srv/opentallas-scratch2/claude/codex-ds-legacy-xs-gate-0538
cd "$R"
python3 prepare.py
python3 make_tb.py
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=(+define+DSFD_PQ_STATIC_X2 +define+S81CTRL_SRAM_FIFO +define+S81CTRL_SRAM_P192 +define+S81CTRL_NATIVE32 +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF +define+OT_S81ENG_TAP_N32R2 +define+OT_S81SL_KV_TRANSPORT +define+OT_SVC_ALLQ +define+SU_SMU_T +define+OT_ATTN_HCORE +define+OT_S81ENG_RR_N32 +define+OT_S81C_HCORE_CTLA +define+OT_S81C_HCORE_RST_TIMED +define+S81_HOSTB_LAND_OBS +define+OT_S81_SH_SRAM +define+OT_S81_SH_RSZ +define+OT_S81_SH_P192 +define+OT_S81_SH_APIPE9 +define+OT_S81_SH_APIPE10)
for f in xs_original xs_candidate xg_original xg_candidate; do "$V" -E -P +define+SYNTHESIS "${D[@]}" "$f.sv" > "$f.synth.v"; done
python3 - <<'PY'
from pathlib import Path
import json
for family in ['xs','xg']:
 old=Path(f'{family}_original.synth.v').read_text();new=Path(f'{family}_candidate.synth.v').read_text()
 new=new.replace('#(parameter INSTANCE = "")','').replace('#(.INSTANCE(INSTANCE))','')
 assert ''.join(old.split())==''.join(new.split()),family+' non-selector SYNTHESIS change'
Path('synthesis_check.json').write_text(json.dumps(dict(status='PASS_SYNTHESIS_BODY_IDENTICAL',only_unused_INSTANCE_declaration_or_propagation=True,added_state_or_stages=0),indent=2)+'\n')
PY
/usr/bin/time -v "$V" --binary --timing -O1 -j 2 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-MULTITOP --output-split 20000 --output-split-cfuncs 2000 "${D[@]}" --top-module tb -Mdir "$R/obj" -f sources.f > build.log 2> build.err
"$R/obj/Vtb" +OT_ROM_DIR="$R/images" > positive.log 2>&1
set +e
"$R/obj/Vtb" +OT_ROM_DIR="$R/wrong_prefix" > wrong_prefix.log 2>&1
p=$?
"$R/obj/Vtb" +OT_ROM_DIR="$R/wrong_image" > wrong_image.log 2>&1
i=$?
set -e
printf '%s\n' "$p" > wrong_prefix.rc
printf '%s\n' "$i" > wrong_image.rc
[[ "$p" != 0 && "$i" != 0 ]]
grep -q PASS_NATIVE_LEGACY_XG_XS_PREFIX positive.log
grep -q LEGACY_NATIVE_IMAGE_MISMATCH wrong_prefix.log
grep -q LEGACY_NATIVE_IMAGE_MISMATCH wrong_image.log
