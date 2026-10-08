#!/bin/bash
set -u
export PYTHONDONTWRITEBYTECODE=1
job=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1
src=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-source-r1
cd "$src" || exit 74
python3 "$job/fresh_guard.py" || exit $?
test -z "$(git status --porcelain)" || exit 76
test ! -f "$job/route.started" || exit 77
python3 "$job/validate_model.py" > "$job/preflight_model.json" || exit 78
mkdir -p "$job/work/orfs/tmp" "$job/tmp"
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 TMPDIR="$job/tmp"
date -u > "$job/route.started"
python3 tools/run_abi3_physical_aligned_guarded.py --macro-track-gate --view asap7 --top ot_hbm_integrated_su_cp_context --param ENABLE=1 --param SU_ENABLE=1 --param SU_REGISTERED_OUTPUTS=1 --param SU_REGISTERED_STATUS=1 --param SU_REGISTERED_BOUNDARY=1 --param SU_BALANCED_OWNER_BOUNDARY=1 --source rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv --source rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_header_decode.sv --source rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_bind.sv --source rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_association.sv --source rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_context.sv --clock-period-ns 0.833333333333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --io-delay-fraction 0.2 --core-input-delay-min-ns 0 --core-input-delay-max-ns 0.166666666667 --output-delay-min-ns 0 --output-delay-max-ns 0.166666666667 --sdc-append physical/hbm_cp_parent_context_20261005/context.sdc --die-area 0 0 77.76 77.76 --core-area 17.28 17.28 60.48 60.48 --step-tcl POST_IO_PLACEMENT=physical/hbm_cp_parent_context_20261005/pins_and_regions.tcl --orfs-var PDN_TCL=/src/physical/hbm_cp_parent_context_20261005/pdn.tcl --routing-layers M2 M7 --orfs-var IO_PLACER_H=M6 --orfs-var IO_PLACER_V=M7 --corner TT --orfs-corner WC --hold-corners WC,BC --max-transition-ns 0.320 --max-fanout 32 --hold-margin-ns 0.010 --stages pnr --place-density 0.50 --orfs-var NUM_CORES=16 --orfs-var TMPDIR=/work/tmp --orfs-var ADDER_MAP_FILE= --keep-heavy-artifacts --nickname-tag harvey_cp_parent_context_r1 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir /srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1/work --output /srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1/physical.json > "$job/route.log" 2>&1
rc=$?;echo "$rc" > "$job/route.exit"
if find "$job/work" -name 6_final.odb -print -quit | rg -q .; then
 python3 tools/hbm_cp_parent_context.py --corner-sta "$job/work/orfs" --output "$job/corner_sta.json" > "$job/corner_sta.log" 2>&1
 echo "$?" > "$job/corner.exit"
fi
echo "$rc" > "$job/terminal.exit"
exit "$rc"
