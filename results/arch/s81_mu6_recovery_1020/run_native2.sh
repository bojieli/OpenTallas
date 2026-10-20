#!/bin/bash
set -uo pipefail
A=/srv/opentallas-scratch/claude/codex-s81-gunit-ro3-audit
S=/srv/opentallas-scratch/claude/closure-loop/dsdv_gunit_l5_ro3-ro3-648ee10c0
R=$S/routes/dsdv_gunit_l5_ro3_ro3_648ee10c0/work/orfs
B=results/asap7/opentallas_dsdv_gunit_l5_asap7_ref_dsdv_gunit_l5_ro3_ro3_648ee10c0/base
sha256sum "$R/$B/6_final.odb" "$R/$B/6_final.v" "$A/tools/ref_tile/native_census.py" "$A/tools/textbook_lint.py" > "$A/input_hashes.txt"
docker run --rm --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v "$A:/audit" -v "$R:/work:ro" -e "AUDIT_ODB=/work/$B/6_final.odb" openroad/orfs:asap7lock -no_init -exit -python /audit/final_geometry.py > "$A/final_geometry.log" 2>&1
printf 'GEOMETRY_RC %s\n' "$?"
docker run --rm --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v "$A:/audit" -v "$R:/work:ro" -e "AUDIT_ODB=/work/$B/6_final.odb" openroad/orfs:asap7lock -no_init -exit /audit/pg_trial.tcl > "$A/pg_trial.log" 2>&1
printf 'PG_TRIAL_RC %s\n' "$?"
docker run --rm --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v "$A:/audit" -e AUDIT_ODB=/audit/trial_global_connect.odb -e AUDIT_OUT=/audit/trial_geometry.json openroad/orfs:asap7lock -no_init -exit -python /audit/final_geometry.py > "$A/trial_geometry.log" 2>&1
printf 'PG_TRIAL_AUDIT_RC %s\n' "$?"

docker run --rm --entrypoint bash -v "$A:/audit" -v "$R:/work:ro" -v "$S/src:/src:ro" openroad/orfs:asap7lock -c 'args=(); for f in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*; do args+=(--liberty "$f"); done; python3 /audit/tools/ref_tile/native_census.py --netlist /work/results/asap7/opentallas_dsdv_gunit_l5_asap7_ref_dsdv_gunit_l5_ro3_ro3_648ee10c0/base/6_final.v --top dsdv_gunit_l5 "${args[@]}" --liberty /audit/macro_tt.lib --out /audit/final_native_census.json' > "$A/final_native_census.log" 2>&1
printf 'NATIVE_RC %s\n' "$?"
