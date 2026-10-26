#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
run() { docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -python -exit "$@"; }
run /work/prepare_guards.py > "$D/guard3_prepare.log" 2>&1
run /work/infra_replay.py --source /work/source.odb --target /work/target.odb --nets /work/nets.txt --out /work/guard3_combined.odb > "$D/guard3_import.log" 2>&1
docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -no_init -exit /work/guard3_grt.tcl > "$D/guard3_grt.log" 2>&1
run /work/infra_replay.py --verify /work/guard3_after.odb --against /work/guard3_combined.replay.json > "$D/guard3_verify.log" 2>&1
if run /work/infra_replay.py --source /work/source.odb --target /work/guard_target_data_on_protected_pin.odb --nets /work/nets.txt --out /work/guard3_should_reject_data.odb > "$D/guard3_data_rejected.log" 2>&1; then echo BAD_DATA_MUTANT_PASSED; exit 1; fi
grep -q 'attaches protected infrastructure terminal' "$D/guard3_data_rejected.log"
if run /work/infra_replay.py --source /work/source.odb --target /work/guard_target_provisional_clock.odb --nets /work/nets.txt --out /work/guard3_should_reject_unlisted.odb > "$D/guard3_unlisted_rejected.log" 2>&1; then echo UNLISTED_PROVISIONAL_PASSED; exit 1; fi
grep -q 'attaches protected infrastructure terminal' "$D/guard3_unlisted_rejected.log"
run /work/infra_replay.py --source /work/source.odb --target /work/guard_target_provisional_clock.odb --nets /work/nets.txt --out /work/guard3_provisional_accepted.odb --provisional-nets /work/guard_provisional.txt > "$D/guard3_provisional_accepted.log" 2>&1
run /work/infra_replay.py --source /work/guard_source_already_dnt.odb --target /work/target.odb --nets /work/nets.txt --out /work/guard3_already_dnt_accepted.odb > "$D/guard3_already_dnt_accepted.log" 2>&1
echo ACTUAL_GUARD_VEHICLE_PASS
