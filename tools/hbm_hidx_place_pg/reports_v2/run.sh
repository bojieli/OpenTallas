#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
sha256sum -c output/checkpoint.sha256
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
runner=(docker run --rm --network none --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$image")
failed=0
attempt() { local label="$1";shift;local rc=0;"$@" >"output/$label.log" 2>&1 || rc=$?;echo "$label $rc" >>output/reports_v2_status;if ((rc));then failed=1;fi; }
attempt metal_v2 "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/reports_v2/export_metal.py /work/output/pg_checkpoint.odb /work/output
attempt empty_pg_causal "${runner[@]}" python3 kit/reports_v2/empty_pg_policy.py
attempt conductor_v2 "${runner[@]}" bash -lc 'cd output;python3 ../kit/prove_metal_readonly.py'
attempt strict_v2 "${runner[@]}" bash -lc 'cd output/native;PYTHONPATH=/work/kit python3 /work/kit/vendor/strict_replay.py . /work/output/strict_v2'
attempt geometry_identity "${runner[@]}" python3 kit/report_readonly.py
attempt checkpoint_immutable_v2 sha256sum -c output/checkpoint.sha256
if ((failed));then exit 1;fi
echo 'READONLY_SUCCESSOR_COMPLETE_ORIGINAL_REFUSALS_PRESERVED_NO_CTS_NO_ROUTE' >output/reports_v2_verdict
