#!/bin/bash
set -uo pipefail
B=/srv/opentallas-scratch2/claude/codex-clock-components-1028
K=/srv/opentallas-scratch2/claude/die-kv-21-1028/kit_c
pids=()
for C in TT FF; do
  docker run --rm --name codex-kv-components-$C --memory=32g --memory-swap=32g --cpus=4 -e CORNER=$C \
    -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v "$K":/work:ro -v "/srv/opentallas-scratch2/claude/die-kv-21-1028/out_c_$C":/input:ro \
    -v "$B":/out openroad/orfs:asap7lock \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/read_$C.tcl" \
    > "$B/read_$C.log" 2>&1 &
  pids+=("$!")
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=$?; done
echo "$rc" > "$B/status"
exit "$rc"
