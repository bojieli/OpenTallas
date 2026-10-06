#!/bin/bash
# Handed existing W2 sink component route. Execute ONLY after Kepler releases a slot.
set -eu
if test "$#" -lt 3; then
 echo 'usage: bash nash-w2-sink-registered-route-r1.sh TOOL_CHECKOUT UNIQUE_JOB CHANGED_SOURCE_ROOT [ADMIT_SH]' >&2
 exit 2
fi
tools_root=$1
job=$2
source_root=$3
admit=${4:-/srv/opentallas-scratch/admit.sh}
test -x "$admit"
test -f "$tools_root/tools/run_abi3_physical_aligned_guarded.py"
test -f "$tools_root/tools/w18/corner_sta.py"
test -f "$source_root/rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv"
test -f "$source_root/rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_result_sink.sv"
mkdir "$job"
mkdir -p "$job/tmp" "$job/work/orfs/tmp"
export TMPDIR="$job/tmp" NUM_CORES=16 OT_ORFS_NUM_CORES=16
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
cd "$tools_root"
# 16 GiB conservative admission reservation, NOT a measured P&R peak or process cap.
# All original ports are timed. No reset/IO exceptions or constant parent grants.
set +e
"$admit" 16 -- python3 tools/run_abi3_physical_aligned_guarded.py --macro-track-gate \
 --view asap7 --top ot_hbm_integrated_w2_result_sink --param ENABLE=1 --param REGISTERED_SUBBLOCKS=1 \
 --source-root "$source_root" --source rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv \
 --source rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_result_sink.sv \
 --clock-port clk --clock-period-ns 0.833333 \
 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --io-delay-fraction 0.2 --corner TT --orfs-corner WC --hold-corners WC,BC \
 --max-transition-ns 0.320 --max-fanout 32 --hold-margin-ns 0.010 \
 --stages pnr --core-utilization 25 --place-density 0.5 \
 --orfs-var NUM_CORES=16 --orfs-var TMPDIR=/work/tmp --orfs-var ADDER_MAP_FILE= \
 --keep-heavy-artifacts --nickname-tag nash_w2_sink_registered_72c067c9c_r1 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$job/work" --output "$job/physical.json" > "$job/route.log" 2>&1
route_rc=$?
printf 'route_rc=%s\n' "$route_rc" > "$job/terminal.rc"
if find "$job/work" -name 6_final.odb -print -quit | rg -q .; then
 python3 tools/w18/corner_sta.py --orfs-dir "$job/work/orfs" --output "$job/corner_sta.json" > "$job/corner_sta.log" 2>&1
 corner_rc=$?
 printf 'corner_rc=%s\n' "$corner_rc" >> "$job/terminal.rc"
else
 printf 'corner_sta=not_run_no_final_odb\n' >> "$job/terminal.rc"
fi
exit "$route_rc"
