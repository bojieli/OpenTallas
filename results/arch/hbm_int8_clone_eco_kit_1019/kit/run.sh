#!/bin/bash
# Not yet authorized. Fleet invocation only after exact ROOT grant.
set -euo pipefail
: "${INT8_ECO_WORK:?isolated staged immutable packet}"
: "${INT8_ECO_BASELINE:?immutable V2 snapshot}"
: "${INT8_ECO_ROOT_APPROVAL:?fresh exact ROOT grant}"
python3 "$INT8_ECO_WORK/kit/validate_inputs.py" "$INT8_ECO_WORK" "$INT8_ECO_ROOT_APPROVAL" "$INT8_ECO_BASELINE"
mkdir "$INT8_ECO_WORK/output"
out="$INT8_ECO_WORK/output";mkdir "$out/census"
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
runner=(docker run --rm --user "$(id -u):$(id -g)" -v "$INT8_ECO_WORK/kit:/kit:ro" -v "$INT8_ECO_BASELINE:/baseline:ro" -v "$out:/output" "$image")
failed=0
attempt() {
 local label="$1";shift;local rc=0
 "$@" > "$out/$label.log" 2>&1 || rc=$?
 printf '%s %s\n' "$label" "$rc" >> "$out/stage_exit_status"
 if ((rc));then failed=1;fi
}
# Freeze actual baseline before one mutation, and verify native image platform.
sha256sum "$INT8_ECO_BASELINE/output/cts_checkpoint.odb" > "$out/baseline.sha256"
attempt platform "${runner[@]}" bash -lc 'sha256sum -c /kit/lib_SHA256SUMS && sha256sum -c /kit/platform_SHA256SUMS'
if ((failed));then exit 1;fi
# SINGLE mutation attempt. No optimization, legalization repair, CTS, route or retry.
attempt clone_eco "${runner[@]}" bash -lc 'INT8_EXACT_ECO_AUTHORIZED=INT8_CLONE_ECO_FEB988_V1 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /kit/clone_eco.tcl'
if [[ ! -s "$out/eco_pg_checkpoint.odb" || ! -s "$out/checkpoint.status" ]];then exit 1;fi
sha256sum "$out/eco_pg_checkpoint.odb" "$out/eco_pg_checkpoint.v" > "$out/checkpoint.sha256"
# Reports cannot discard/rewrite the PG-checked checkpoint; failures remain immutable.
attempt raw "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /kit/export_raw.py /output/eco_pg_checkpoint.odb /output/native
attempt graph python3 "$INT8_ECO_WORK/kit/prove_topology.py" "$out/native"
attempt metal_export "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /kit/export_metal.py /output/eco_pg_checkpoint.odb /output
attempt conductor "${runner[@]}" bash -lc 'cd /output;python3 /kit/prove_metal_readonly.py'
attempt strict "${runner[@]}" bash -lc 'cp /kit/inputs/native_libs/* /output/native/;cd /output/native;sha256sum raw.json *.lib* > SHA256SUMS;python3 /kit/vendor/strict_replay.py . /output/strict'
for co in TT FF;do
 attempt census_$co "${runner[@]}" bash -lc "INT8_CORNER=$co /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /kit/census.tcl"
 attempt clock_$co "${runner[@]}" bash -lc "INT8_CORNER=$co /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /kit/clock_all.tcl"
done
attempt acceptance python3 "$INT8_ECO_WORK/kit/native_acceptance.py" "$out"
attempt source_truth python3 "$INT8_ECO_WORK/kit/reset_truth.py"
attempt fixtures env INT8_FIXTURE_OUTPUT="$out/fixtures" bash "$INT8_ECO_WORK/kit/run_fixtures.sh"
attempt immutable sha256sum -c "$out/checkpoint.sha256"
attempt baseline_immutable sha256sum -c "$out/baseline.sha256"
printf 'EXACT_CLONE_NATIVE_DIAGNOSTIC_REVIEW_REQUIRED failed=%s NO_PUBLICATION_NO_ADOPTION\n' "$failed" > "$out/status"
exit "$failed"
