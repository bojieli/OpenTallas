#!/usr/bin/env bash
# Centre-aligned forwarded-clock station route. VARIANT a: 140x140 um, data pins 1 track apart;
# VARIANT b: 180x180 um, data pins 2 tracks apart (pin-spread, lower density).
set -euo pipefail
LABEL=${1:?label}; OUT=${2:?bulk output}; SRC=${SRC:?pinned source root}; VARIANT=${VARIANT:-a}
cd "$SRC"
export OPENTALLAS_ORFS_IMAGE=openroad/orfs:asap7lock
W="$OUT/$LABEL"; mkdir -p "$W"
P=physical/qwen_link_fwd_cx_station
if [ "$VARIANT" = b ]; then D=180; MD=2; DENS=0.45; else D=140; MD=1; DENS=0.55; fi
C=$(python3 -c "print($D-2.16)"); HI=$(python3 -c "print($D-14)"); CL=$(python3 -c "print($D-12)"); CH=$(python3 -c "print($D-4)")
python3 "$P/prepare.py" --out "$W/frontend"
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_link_fwd_cx_station \
 --source rtl/physical/ot_qwen_link_fwd_cx_tmr.sv \
 --die-area 0 0 $D $D --core-area 2.16 2.16 $C $C \
 --pin-region "^(ab_i|ba_o)(\[|$)=left:4-$HI" \
 --pin-region "^(ab_o|ba_i)(\[|$)=right:4-$HI" \
 --pin-region "^(fclk_ab_i|fclk_ba_o|rst_n)$=left:$CL-$CH" \
 --pin-region "^(fclk_ba_i|fclk_ab_o)$=right:$CL-$CH" \
 --routing-layers M2 M7 --clock-port fclk_ab_i --clock-period-ns 0.833333333333 \
 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 \
 --stages synth,pnr --place-density $DENS --hold-margin-ns 0.015 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=8 \
 --orfs-var "SDC_FILE=/src/$P/clocks.sdc" \
 --orfs-var "PLACE_PINS_ARGS=-min_distance $MD -min_distance_in_tracks" \
 --step-tcl POST_CTS="$P/propagate.tcl" \
 --step-tcl PRE_GLOBAL_ROUTE="$P/propagate.tcl" \
 --step-tcl POST_DETAIL_ROUTE="$P/audit.tcl" \
 --slew-margin-percent 30 --purpose signoff_target --nickname-tag "qfcx${VARIANT}_$LABEL" \
 --keep-workdir "$W/work" --output "$W/physical.json" > "$W/flow.log" 2>&1
python3 "$P/signoff.py" --orfs-dir "$W/work/orfs" --output "$W/corner_sta.json" > "$W/signoff.log" 2>&1
printf 'flow_rc=0\ncorner_rc=0\n' > "$W/status"
