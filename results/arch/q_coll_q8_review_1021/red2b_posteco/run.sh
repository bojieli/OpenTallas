#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/closure-loop/qfd_dv_s5_red2b-red2bk-134f1aa89
D=/srv/opentallas-scratch/claude/codex-q-red2b-posteco-1021
B=$R/routes/qfd_dv_s5_red2b_red2bk_134f1aa89/work/orfs/results/asap7/opentallas_qfd_dv_s5_red2_leaf_asap7_ref_qfd_dv_s5_red2b_red2bk_134f1aa89/base
IMAGE=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
sha256sum "$B/6_final.odb" "$B/6_final.sdc" "$B/6_final.spef" "$R/routes/qfd_dv_s5_red2b_red2bk_134f1aa89/work/orfs/config.mk" "$R/src/tools/closure_loop/ck_insertion.py" "$R/src/physical/common_flow/clock_family.tcl" "$D/native_audit.py" "$R"/record/views/qfd_dv_s5_red2_leaf/*.lib > "$D/before.sha256"
printf '%s\n' 'c2aa562173daf8df071c548aa9f1b02fc4a1f3ba3ed70b40a0c370fbb50e8fb8' > "$D/expected_odb.sha"
ACTUAL=$(sha256sum "$B/6_final.odb" | cut -d ' ' -f1)
test "$ACTUAL" = "$(cat "$D/expected_odb.sha")"
docker run --rm --memory 48g -v "$D:/job" -v "$B:/final:ro" "$IMAGE" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /job/native_audit.py /final/6_final.odb /job/native > "$D/native.log" 2>&1
python3 "$R/src/tools/closure_loop/ck_insertion.py" --base "$B" --routed --all-clocks --raw-source --route-corner TT --image "$IMAGE" --output "$D/routed_clock.json" > "$D/clock.log" 2>&1
sha256sum -c "$D/before.sha256" > "$D/after_verify.log"
printf '%s\n' 'READONLY_AUDITS_COMPLETED'
