#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/closure-loop/smh_own_eg_ref-own3-a71aa3fa4/routes/smh_own_eg_ref_own3_a71aa3fa4/work/orfs/results/asap7/opentallas_ot_smh_own_eg_asap7_ref_smh_own_eg_ref_own3_a71aa3fa4/base
out=/tmp/codex-hbm-vm-sm-2240/own3_postroute
docker image inspect openroad/orfs:latest --format '{{.Id}}' > "$out/image_id.txt"
sha256sum "$base/6_final.odb" > "$out/odb_sha256_before.txt"
docker run --rm -v "$base:/in:ro" -v "$out:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/canonical_export.tcl > "$out/canonical_export.log" 2>&1
cat "$out/canonical_export.log"
sha256sum "$base/6_final.odb" > "$out/odb_sha256_after.txt"
cmp "$out/odb_sha256_before.txt" "$out/odb_sha256_after.txt"
