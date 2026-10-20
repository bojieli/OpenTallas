#!/bin/bash
set -euo pipefail
A=/srv/opentallas-scratch/claude/codex-qw-coll-clock-1020
R=/srv/opentallas-scratch/claude/ref_gate/qfd_coll_split_q4w-20261019-213247
I=$(find "$R/routes" -name 1_synth.odb)
sha256sum "$I" > "$A/input.sha256"
docker run --rm --network none -v "$A:/work" -v "$R:/input:ro" -e OT_CENSUS_ODB="/input/${I#"$R/"}" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /work/native_dump.tcl > "$A/native.log" 2>&1
sha256sum -c "$A/input.sha256"
