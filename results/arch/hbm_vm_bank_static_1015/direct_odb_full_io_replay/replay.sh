#!/usr/bin/env bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/vms_bank_static_rg7wg3_1015-20261015-022055
OUT=/var/tmp/vms_bank_direct_full_io_1015
mkdir -p "$OUT"
cp -a "$R/routes/gate/work/orfs" "$OUT/work"
rm -f "$OUT/work/results/asap7/opentallas_hfd_vms_bank_static_rg7wg3_asap7_ref_gate/base/3_2_place_iop.odb"
docker run --rm -v "$R/src:/src:ro" -v "$OUT/work:/work" -v /var/tmp/vms_bank_direct_candidate.tcl:/src/rtl/hbm_accel/generic/vm/static/physical/native_bank_pin_audit.tcl:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=1 /work/results/asap7/opentallas_hfd_vms_bank_static_rg7wg3_asap7_ref_gate/base/3_2_place_iop.odb' > "$OUT/run.log" 2>&1
tail -8 "$OUT/run.log"
