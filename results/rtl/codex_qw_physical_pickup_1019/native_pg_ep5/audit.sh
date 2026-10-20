#!/bin/bash
set -u
A=/srv/opentallas-scratch/claude/codex-qw-physical-pickup-1019
for name in qfd_sys_face_bc3-20261019-220802 qfd_sys_face_bc3c-20261019-220802 qfd_d2d_static_sf7w-20261019-221652 qfd_sys_face-20261019-223453; do
 R=/srv/opentallas-scratch/claude/ref_gate/$name
 [ -d "$R" ] || continue
 for odb in $(find "$R/routes" -name '4_cts.odb' -o -name '5_1_grt*.odb'); do
  tag=${name}_$(basename "$odb" .odb)
  [ ! -e "$A/$tag.json" ] || continue
  sha256sum "$odb" > "$A/$tag.sha256"
  docker run --rm -v /srv:/srv -v "$A:/audit:ro" -e OT_PG_AUDIT_ODB="$odb" -e OT_PG_AUDIT_REPORT="$A/$tag.json" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/audit_native_pg.tcl > "$A/$tag.log" 2>&1
  echo "$tag RC=$?"
  sha256sum -c "$A/$tag.sha256"
 done
done
