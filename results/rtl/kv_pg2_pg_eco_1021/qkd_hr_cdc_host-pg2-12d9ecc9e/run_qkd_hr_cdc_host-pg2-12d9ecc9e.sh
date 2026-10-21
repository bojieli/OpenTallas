#!/bin/bash
set -euo pipefail
out=/srv/opentallas-scratch/claude/gskq-pgrr/qkd_hr_cdc_host-pg2-12d9ecc9e/pg_bind_eco_native
odb=/srv/opentallas-scratch/claude/gskq-pgrr/stage/in_host/6_final.odb
mkdir -p "$out"
test ! -e "$out/post_audit.json"
cp /srv/opentallas-scratch/claude/gskq-pgrr/stage/pg_bind_eco.tcl /srv/opentallas-scratch/claude/gskq-pgrr/stage/native_pg_binding.tcl "$out/"
sha256sum "$odb" > "$out/input.before.sha256"
docker run --rm --network none -v "${odb%/*}:/input:ro" -v "$out:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /out/pg_bind_eco.tcl > "$out/run.log" 2>&1
cmp "$out/pre_signal.txt" "$out/post_signal.txt"
echo SIGNAL_IDENTICAL >> "$out/run.log"
sha256sum "$odb" > "$out/input.after.sha256"
cmp "$out/input.before.sha256" "$out/input.after.sha256"
cd "$out"; sha256sum 6_final_pgbound.odb pre_signal.txt post_signal.txt >> run.log
echo RC=0 >> run.log; tail -12 run.log
