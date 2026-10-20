#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/qfd_sys_face_bc2l-20261019-114348
D=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for C in tt ff; do
 docker run --rm -e OT_GATE_SIGNOFF_SDC=/src/physical/ref_tile/qfd_sys_face_bc2l/signoff.sdc -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work" -v "$R/terminal_probe_$C.tcl:/probe.tcl:ro" "$D" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe.tcl > "$R/terminal_native_$C.log" 2>&1
done
 docker run --rm -e PG_ODB=/work/results/asap7/opentallas_qfd_sys_face_control_safe_asap7_ref_gate/base/5_1_grt.odb -e PG_OUT=/work/terminal_pg -v "$R/routes/gate/work/orfs:/work" -v "$R/terminal_pg.py:/probe.py:ro" "$D" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /probe.py > "$R/terminal_pg.log" 2>&1
