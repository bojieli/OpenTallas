#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/claude/hidx-place-pg-1019
sha256sum -c output/checkpoint.sha256
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
runner=(docker run --rm --network none --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$image")
failed=0
attempt() { local label="$1";shift;local rc=0;"$@" >"output/$label.log" 2>&1 || rc=$?;echo "$label $rc" >>output/reports_v3_status;if ((rc));then failed=1;fi; }
attempt strict_v3 "${runner[@]}" bash -lc 'mkdir output/native_v3;cp output/native/raw.json output/native_v3/;p=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM;cp $p/asap7sc7p5t_{AO,OA,SIMPLE}_RVT_TT_nldm_211120.lib.gz $p/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz $p/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib output/native_v3/;cd output/native_v3;sha256sum raw.json *.lib* >SHA256SUMS;PYTHONPATH=/work/kit:/work/kit/vendor python3 /work/kit/reports_v3/strict_replay.py . /work/output/strict_v3'
attempt geometry_identity_v3 "${runner[@]}" python3 kit/report_readonly.py
attempt checkpoint_immutable_v3 sha256sum -c output/checkpoint.sha256
if ((failed));then exit 1;fi
echo 'STRICT_HIDX_TOP_LIB_DEPENDENCY_SUCCESSOR_COMPLETE_SOURCE_NETWORK_IDENTICAL' >output/reports_v3_verdict
