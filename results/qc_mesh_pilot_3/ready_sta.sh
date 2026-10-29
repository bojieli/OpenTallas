#!/bin/bash
# Re-time only completed DRT clips copied into an owned run directory.
# Usage: ready_sta.sh CLIPROOT; rerun after adding completed clips.
set -euo pipefail
R=$(realpath "$1")
sta() {
  local clip=$1 corner=$2 slew=$3 mid=$4
  python3 - "$R/$clip" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
# OpenRCX emits an empty optional *CONN section for disconnected mesh fragments.
# OpenSTA rejects that token sequence. Keep every CAP/RES record byte-identical.
raw = (p/'drt.spef').read_text()
clean = raw.replace('*CONN\n*CAP\n', '*CAP\n')
(p/'sta_input.spef').write_text(clean)
tcl = (p/'sta.tcl').read_text().replace('read_spef /o/drt.spef', 'read_spef /o/sta_input.spef')
tcl = tcl.replace('set fh [open', 'report_checks -path_delay max -group_path_count 1\nset fh [open', 1)
(p/'sta_input.tcl').write_text(tcl)
PY
  docker run --rm --name "codex-qcmp3-$(basename "$R")-$clip-$corner-$$" \
    --memory=8g --memory-swap=8g --cpus=2 \
    -e CORNER="$corner" -e SLEW="$slew" -e MID="$mid" -e TAG= \
    -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v "$R/$clip:/o" openroad/orfs:asap7lock bash -lc \
    'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /o/sta_input.tcl > /o/sta_$CORNER.log 2>&1; rc=$?; chown -R 1000:1000 /o; exit $rc'
  grep -q OT_STA_DONE "$R/$clip/sta_$corner.log"
}
for C in TT FF; do
  sta mid "$C" 0 1
  for c in c0 c1 c2 c3 core; do
    if ! test -f "$R/$c/drt.odb"; then echo "PENDING $c"; continue; fi
    e=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["entry"])' "$R/$c/clip.json")
    sl=$(awk -v e="$e" '$1=="A" && $2==e {print $5}' "$R/mid/tree_drt_$C.txt")
    test -n "$sl"
    echo "$C $c entry $e slew $sl"
    sta "$c" "$C" "$sl" 0
  done
done
