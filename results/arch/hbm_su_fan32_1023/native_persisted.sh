#!/bin/bash
set -euo pipefail
HERE=$(pwd)
docker run --rm -v "$HERE/src:/src:ro" -v "$HERE/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work RESULTS_DIR=/work/results/asap7/opentallas_ot_hbm_su_static_pgslice_rgf_lp_n32_asap7_ref_gate/base OBJECTS_DIR=/work/objects LOG_DIR=/work/logs REPORTS_DIR=/work/reports synth > full_native_synth_persisted.log 2>&1 || true
test -f work/results/asap7/opentallas_ot_hbm_su_static_pgslice_rgf_lp_n32_asap7_ref_gate/base/1_2_yosys.v
docker run --rm -v "$HERE/src:/src:ro" -v "$HERE/work:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 python3 /work/audit.py > full_native_audit.log 2>&1
