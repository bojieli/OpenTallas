#!/bin/bash
set -euo pipefail
label=$1;shift
work=$OUT/$label
mkdir -p "$work"
for item in physical.json run.log exit corner_sta.json work;do
 if [[ -e "$work/$item" ]];then echo "Refusing immutable prior evidence $work/$item" >&2;exit 73;fi
done
cd "$SRC"
export NUM_CORES=${CORES:-12} OT_ORFS_NUM_CORES=${CORES:-12}
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
/srv/opentallas-scratch/admit.sh ${NEED:-24} -- python3 tools/run_abi3_physical.py \
 --view asap7 --top ot_s81_native_pc_mux --param ENABLE=1 \
 --source rtl/dsrom_sys/s81_ingest/ot_s81_native_pc_mux.sv --source rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv \
 --clock-port ck --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append physical/s81_native_ingest/native_pc.sdc \
 --stages pnr --die-area 0 0 240 480 --core-area 0.54 0.54 239.46 479.46 --place-density 0.55 --routing-layers M2 M7 \
 --pin-region '^src_.*=top' --pin-region '^(rq|rk|wd|rv|r_data|r_tag|r_beat|ctrl_live)(\[.*\])?$=bottom' \
 --pin-region '^(ck|rst_n)$=left' --pin-region '^(fault|ce|pending)$=right' --pin-regions-exhaustive \
 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 60 --hold-margin-ns 0.05 \
 --purpose pathfinding --nickname-tag "$label" --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 "$@" --keep-workdir "$work/work" --output "$work/physical.json" >"$work/run.log" 2>&1
printf 'rc=0\n' >"$work/exit"
case " $* " in *" --pnr-stop-after "*)exit 0;;esac
python3 tools/w18/corner_sta.py --post-sdc physical/s81_native_ingest/native_pc.sdc --orfs-dir "$work/work/orfs" \
 --output "$work/corner_sta.json" >"$work/corner.log" 2>&1
printf 'corner_rc=0\n' >>"$work/exit"
