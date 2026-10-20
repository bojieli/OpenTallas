#!/bin/bash
set -euo pipefail
lane=$PWD
run=/srv/opentallas-scratch/claude/closure-loop/qkd_kvs_hroot_s32v4-v4a-295504c93
orfs=$(ls -d "$run"/routes/*/work/orfs)
base=$(ls -d "$orfs"/results/asap7/*/base)
kit=$run/src/physical/ref_tile/qkd_kvs_hroot_s32v4
mkdir -p private_view
sha256sum "$base/6_final.odb" "$base/6_final.spef" "$base/6_final.sdc" > inputs_before.sha256
docker image inspect openroad/orfs:latest --format '{{.Id}}' > image.txt
image=$(cat image.txt)
python3 toolsrc/tools/tt_views/view_export.py --orfs-dir "$orfs" --name qkd_kvs_hroot_safe32 --out "$lane/private_view" --interface-sdc "$kit/signoff.sdc" --image "$image" --corners ss,ff,tt --src "$run/src" --post-sdc "$kit/signoff.sdc" --post-sdc "$run/src/physical/common_flow/link_budget_consistent.sdc" --post-sdc "$run/src/physical/common_flow/io_ref_routed.sdc" --expect-tt 255.79 --expect-ff 16.62
python3 toolsrc/tools/closure_loop/ck_insertion.py --base "$base" --routed --all-clocks --raw-source --image "$image" --output "$lane/private_view/insertion.json"
sha256sum "$base/6_final.odb" "$base/6_final.spef" "$base/6_final.sdc" > inputs_after.sha256
cmp inputs_before.sha256 inputs_after.sha256
