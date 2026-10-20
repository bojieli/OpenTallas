#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/qfd_d2d_static_sf7w-20261019-221652
A=/srv/opentallas-scratch/claude/codex-qw-critical-1020
I=$(find "$R/routes" -name 5_1_grt.odb)
test -n "$I"
sha256sum "$I" > "$A/input.sha256"
docker run --rm --network none -v "$A:/out" -v "$R:/input:ro" -e OT_INPUT_ODB="/input/${I#"$R/"}" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /out/pg_bind_gate_copy.tcl > "$A/run.log" 2>&1
diff "$A/pre_signal.txt" "$A/post_signal.txt" && echo SIGNAL_IDENTICAL >> "$A/run.log"
sha256sum -c "$A/input.sha256"
sha256sum "$A/gate_grt_pgbound.odb" > "$A/output.sha256"
tail -10 "$A/run.log"
