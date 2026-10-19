#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/claude/hidx-place-pg-1019
sha256sum -c output/checkpoint.sha256
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
runner=(docker run --rm --network none --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$image")
failed=0
attempt() { local label="$1";shift;local rc=0;"$@" >"output/$label.log" 2>&1 || rc=$?;echo "$label $rc" >>output/reports_v4_status;if ((rc));then failed=1;fi; }
attempt geometry_identity_v4 "${runner[@]}" python3 kit/report_readonly.py
attempt pin_geometry "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/export_pin_geometry.py /work/output/pg_checkpoint.odb
attempt pg_signal_short "${runner[@]}" python3 kit/pg_signal_short.py
attempt checkpoint_immutable_v4 sha256sum -c output/checkpoint.sha256
if ((failed));then exit 1;fi
echo 'ALL_READONLY_NATIVE_EVIDENCE_COMPLETE_PLACEMENT_QUALITY_HOLD_NO_CTS' >output/reports_v4_verdict
