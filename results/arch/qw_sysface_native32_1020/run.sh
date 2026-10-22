#!/bin/bash
set -eu
TASK_DIR=/srv/opentallas-scratch2/claude/codex-qw-sysface-review-1020
GATE_DIR=/srv/opentallas-scratch/claude/ref_gate/qfd_sys_face-20261019-223453
for STAGE in 1_synth 5_1_grt; do
 ODB_FILE=routes/gate/work/orfs/results/asap7/opentallas_qfd_sys_face_asap7_ref_gate/base/$STAGE.odb
 test -s "$GATE_DIR/$ODB_FILE"
 docker run --rm -v "$GATE_DIR:/route:ro" -v "$TASK_DIR:/audit" -w /audit openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python native_audit.py /route/$ODB_FILE /audit/$STAGE
 done
