#!/bin/bash
# Fleet only: immutable single execution. Successor needs a NEW exact ROOT grant.
set -euo pipefail
: "${INT8_CTS_WORK:?isolated snapshot path required}"
: "${INT8_CTS_ROOT_APPROVAL:?ROOT grant JSON required}"
python3 "$INT8_CTS_WORK/kit/validate_inputs.py" "$INT8_CTS_WORK" "$INT8_CTS_ROOT_APPROVAL"
mkdir "$INT8_CTS_WORK/output"
out="$INT8_CTS_WORK/output"
printf 'INCOMPLETE\n' > "$out/status"
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
runner=(docker run --rm --user "$(id -u):$(id -g)" -v "$INT8_CTS_WORK:/work" "$image")
failed=0
attempt() {
 local label="$1"; shift
 local rc=0
 "$@" > "$out/$label.log" 2>&1 || rc=$?
 printf '%s %s\n' "$label" "$rc" >> "$out/stage_exit_status"
 if ((rc != 0)); then failed=1; fi
}
attempt platform_check "${runner[@]}" bash -lc 'sha256sum -c /work/kit/platform_SHA256SUMS && sha256sum -c /work/kit/lib_SHA256SUMS'
if ((failed)); then exit 1; fi
attempt pre_export "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/export_raw.py /work/input/placed.odb /work/output/pre_native
if ((failed)); then exit 1; fi
# Exactly ONE CTS attempt. Reporting failure is recorded, never retried.
attempt cts "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/kit/cts_only.tcl
if [[ ! -s "$out/cts_checkpoint.odb" || ! -s "$out/checkpoint.status" ]]; then exit 1; fi
grep -q '^INT8_PG_CHECKED_CTS_CHECKPOINT_V1 ' "$out/checkpoint.status" || exit 1
sha256sum "$out/cts_checkpoint.odb" "$out/cts_checkpoint.v" > "$out/checkpoint.sha256"
# All replay/export commands remain read-only, even after an optional report fails.
attempt ff "${runner[@]}" bash -lc 'INT8_CORNER=FF /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/kit/ff_replay.tcl'
attempt raw_export "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/export_raw.py /work/output/cts_checkpoint.odb /work/output/native
attempt metal_export "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/export_metal.py /work/output/cts_checkpoint.odb /work/output
attempt metal_proof "${runner[@]}" bash -lc 'cd /work/output; python3 /work/kit/prove_metal_readonly.py'
attempt strict "${runner[@]}" bash -lc 'cp /work/input/native_libs/* /work/output/native/; cd /work/output/native; sha256sum raw.json *.lib* > SHA256SUMS; python3 /work/kit/vendor/strict_replay.py . /work/output/strict'
attempt signal_identity python3 "$INT8_CTS_WORK/kit/check_signal_identity.py" "$out/pre_native" "$out/native" "$INT8_CTS_WORK/input/native_libs" "$out/signal_identity.json"
attempt checkpoint_immutable sha256sum -c "$out/checkpoint.sha256"
if ((failed)); then exit 1; fi
attempt check_results python3 "$INT8_CTS_WORK/kit/check_results.py" "$out"
if ((failed)); then exit 1; fi
# Publication is a distinct identity and occurs only after ALL required proofs.
cp --no-clobber "$out/cts_checkpoint.odb" "$out/cts_only.odb"
cp --no-clobber "$out/cts_checkpoint.v" "$out/cts_only.v"
cmp "$out/cts_checkpoint.odb" "$out/cts_only.odb"
sha256sum "$out/cts_only.odb" "$out/cts_only.v" > "$out/publication.sha256"
printf 'BOUNDED_NATIVE_EVIDENCE_COMPLETE_V2_DIAGNOSTIC_ONLY\n' > "$out/status"
