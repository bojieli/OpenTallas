#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/qfd_sys_face_bc2l-20261019-114348
D=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
 docker run --rm -e PG_ODB=/work/results/asap7/opentallas_qfd_sys_face_control_safe_asap7_ref_gate/base/5_1_grt.odb -e PG_OUT=/work/terminal_pg -v "$R/routes/gate/work/orfs:/work" -v "$R/terminal_pg_v2.py:/probe.py:ro" "$D" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /probe.py > "$R/terminal_pg_v2.log" 2>&1
