#!/usr/bin/env bash
set -u
mode=$1
base=/srv/opentallas-scratch/claude/codex-sm-native-fch49
cd "$base/source"
mkdir -p "$base/$mode"
extra=()
if [[ "$mode" == mutant ]]; then extra=(--mut-s1w --expect-fail); fi
ot-heavy --mem 72 -- python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 8 --active 8 --rmax 4096 --req-credit --smh --cg --define OT_SMH_PRODUCTION_SHAPE --define OT_SMH_FC_HIER --define OT_SMH_CG_ENREG --define OT_SMH_XLK --define OT_FP_DATA_NORST --define OT_SMH_DRST0 --define OT_SMH_RSTRELAY --define OT_SMH_HIER --define OT_SMH_PTW_OHDLY --cg-gap 300 --build-jobs 8 --workdir "$base/$mode/build" --out "$base/$mode/result.json" "${extra[@]}" > "$base/$mode/run.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$base/$mode/run.exit"
exit "$rc"
