#!/bin/bash
set -euo pipefail
echo 'PREP ONLY: full geometry classification and ordinary-route scope review pending' >&2
exit 70
# Unreachable candidate native body; no filler/repair/CTS/GRT or finish.
mkdir -p run/results/asap7/kq_qfd_qc_su_lane_w_l7_we89441/base run/reports/asap7/kq_qfd_qc_su_lane_w_l7_we89441/base
cp /srv/opentallas-scratch2/claude/codex-qc-l7-lvt-readout-1102/vclk_ff.sdc vclk_ff.sdc
set +e
docker run --rm --cpus 4 --memory 32g --memory-swap 32g -v /srv/opentallas-scratch2/claude/codex-qc-l7-lvt-readout-1102:/work:ro -v "$PWD":/route -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /route/input_identity.py; python3 /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /route/mm_patch.log; python3 /route/input_adapter.py /OpenROAD-flow-scripts/flow/scripts > /route/INPUT_ADAPTER.json; make DESIGN_CONFIG=/route/config.mk WORK_HOME=/route/run FLOW_VARIANT=base NUM_CORES=4 do-5_2_route' > route.log 2>&1
native_status=$?
set -e
compare_status=1
if [ -s actual_after_route.odb ]; then
 set +e
 docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v /srv/opentallas-scratch2/claude/codex-qc-l7-lvt-readout-1102:/work:ro -v "$PWD":/route -w /route sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /route/compare_route.py' > compare.log 2>&1
 compare_status=$?
 set -e
fi
if [ "$native_status" -ne 0 ]; then exit "$native_status"; fi
exit "$compare_status"
