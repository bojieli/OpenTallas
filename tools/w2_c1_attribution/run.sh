#!/bin/bash
set -euo pipefail
OUT=$1
INPUT=/srv/opentallas-scratch2/scratch/claude/closure-loop/w2-c1-fec1faadd-tt25-existing-odb-eco/c1/eco/pass1/orfs
mkdir -p "$OUT"
cp "$(dirname "$0")/probe.tcl" "$OUT/probe.tcl"
BASE=$INPUT/results/asap7/opentallas_ot_hbm_native_frame_station_rb_asap7_tk_W2_safe_NO2/base
sha256sum "$BASE/6_final.odb" "$BASE/6_final.spef" "$BASE/6_final.sdc" "$OUT/probe.tcl" > "$OUT/input_hashes.sha256"
docker image inspect openroad/orfs:asap7lock > "$OUT/image.json"
set +e
docker run --cidfile "$OUT/container.cid" -v "$INPUT:/work:ro" -v "$OUT:/probe" openroad/orfs:asap7lock bash -lc '/usr/bin/time -v /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/probe.tcl' > "$OUT/probe.log" 2>&1
RC=$?
set -e
printf '{"returncode":%s}\n' "$RC" > "$OUT/exit.json"
docker inspect "$(cat "$OUT/container.cid")" > "$OUT/container_final.json"
exit "$RC"
