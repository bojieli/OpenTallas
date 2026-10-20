#!/bin/bash
set -eu
CASE=$1
ROOT=/srv/opentallas-scratch/claude/codex-qw-sysface4-audit-1020
RUN=/srv/opentallas-scratch/claude/ref_gate/qfd_sys_face_${CASE}-20261020-053946
ODB_FILE=$(find "$RUN/routes/gate/work/orfs/results" -name 5_1_grt.odb)
test -s "$ODB_FILE"
mkdir -p "$ROOT/$CASE"
sha256sum "$ODB_FILE" > "$ROOT/$CASE/odb_before.sha256"
docker run --rm -v "$RUN:/run:ro" -v "$ROOT:/audit" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit/native_audit.py "/run/${ODB_FILE#"$RUN/"}" "/audit/$CASE"
sha256sum "$ODB_FILE" > "$ROOT/$CASE/odb_after.sha256"
cmp "$ROOT/$CASE/odb_before.sha256" "$ROOT/$CASE/odb_after.sha256"
