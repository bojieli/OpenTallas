#!/bin/bash
# Fleet only: unpinned ot-run, isolated snapshot, separate explicit ROOT grant.
set -euo pipefail
: "${INT8_CTS_WORK:?isolated snapshot path required}"
: "${INT8_CTS_ROOT_APPROVAL:?ROOT grant JSON required}"
python3 "$INT8_CTS_WORK/kit/validate_inputs.py" "$INT8_CTS_WORK" "$INT8_CTS_ROOT_APPROVAL"
mkdir "$INT8_CTS_WORK/output"
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
runner=(docker run --rm --user "$(id -u):$(id -g)" -v "$INT8_CTS_WORK:/work" "$image")
"${runner[@]}" bash -lc 'sha256sum -c /work/kit/platform_SHA256SUMS && sha256sum -c /work/kit/lib_SHA256SUMS' > "$INT8_CTS_WORK/output/platform_check.log" 2>&1
"${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/kit/cts_only.tcl > "$INT8_CTS_WORK/output/cts.log" 2>&1
sha256sum "$INT8_CTS_WORK/output/cts_only.odb" > "$INT8_CTS_WORK/output/cts_odb.before.sha"
"${runner[@]}" bash -lc 'INT8_CORNER=FF /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/kit/ff_replay.tcl' > "$INT8_CTS_WORK/output/ff.log" 2>&1
sha256sum -c "$INT8_CTS_WORK/output/cts_odb.before.sha"
"${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/export_raw.py /work/output/cts_only.odb /work/output/native > "$INT8_CTS_WORK/output/raw_export.log" 2>&1
"${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/export_metal.py /work/output/cts_only.odb /work/output > "$INT8_CTS_WORK/output/metal_export.log" 2>&1
"${runner[@]}" bash -lc 'cd /work/output; python3 /work/kit/prove_metal_readonly.py' > "$INT8_CTS_WORK/output/metal_proof.log" 2>&1
"${runner[@]}" bash -lc 'cp /work/input/native_libs/* /work/output/native/; cd /work/output/native; sha256sum raw.json *.lib* > SHA256SUMS; python3 /work/kit/vendor/strict_replay.py . /work/output/strict' > "$INT8_CTS_WORK/output/strict.log" 2>&1
python3 "$INT8_CTS_WORK/kit/check_results.py" "$INT8_CTS_WORK/output"
