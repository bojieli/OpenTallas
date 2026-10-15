#!/bin/bash
# Reference tile / cluster route (tools/ref_tile, ref-flow-1011 2026-10-11).  The kit physical/ref_tile/<name>/kit.env is
# written by tools/ref_tile/ref_tile.py gen; this is the route_master.sh invocation of tools/run_abi3_physical.py (the
# path that closed the Qwen die masters) with the kit's own clock SDC, layer-contract PDN, on-grid placement, an
# EXPLICIT routing-layer range (never a script default over the contract) and composed step hooks:
#   PRE_CTS            io_ref boundary switch after the tree (+ forwarded-clock subtree for clusters that ask for it)
#   PRE_GLOBAL_ROUTE   io_ref boundary + pin-access keepout over the outer face-pin column (adjacent layers)
#   POST_DETAIL_ROUTE  keepout removed (the abstract carries only real metal) + plain boundary restored
# Route over-constrained at ROUTE_PERIOD_NS (0.770); sign-off at 833.333 ps with the kit's signoff.sdc (corner_sta_ref).
# usage: ref_route.sh KIT_ENV LABEL OUTROOT [floorplan|cts]     (SRC = source snapshot root; HM route hold margin, ns)
#   a stop stage runs the flow only that far (pre_route_gate.py --remote uses floorplan; --cts the calibration run)
set -uo pipefail
KITENV=$1; NAME=$2; OUT=$3; STOP=${4:-}
SRC=${SRC:?}; W=$OUT/$NAME; mkdir -p $W; cd $SRC
OT_ENV_PD=${PD:-}; OT_ENV_NC=${NC:-}
source $KITENV
[ -n "$OT_ENV_PD" ] && PD=$OT_ENV_PD; [ -n "$OT_ENV_NC" ] && NC=$OT_ENV_NC
# PIN GROUPS (flowfix 2026-10-13): every run of this script -- the route, the gate's floorplan smoke and its --cts run --
# chunks the --pin-region groups alike.  The job's route command set OT_PIN_GROUP_MAX=32 and the gate did not, so a
# full face passed the gate as one group and died in the route at 3_2_place_iop (PPL-0093: qkd_seq_fan-kc2, ...).
# The kit.env's own `export OT_PIN_GROUP_MAX=` (route.pin_balance) wins, then the caller's, then the route default
# (tools/pin_fit.py ROUTE_PIN_GROUP_MAX; test_pin_fit.py keeps the two equal).
export OT_PIN_GROUP_MAX=${OT_PIN_GROUP_MAX:-32}
K=${KIT#/src/}
D=/src/physical/qwen_die_masters
hook() {
  if [ -f "$K/$1.tcl" ]; then printf '%s' "$K/$1.tcl"; else printf '%s' "physical/qwen_die_masters/$2.tcl"; fi
}
S=(); for f in $SRCS; do S+=(--source $f); done
M=(); for m in "${MACROS[@]}"; do M+=(--macro $m); done
# ASAP7 fastroute.tcl routes clocks on MIN_CLK_ROUTING_LAYER (M4)..MAX_ROUTING_LAYER, and OpenROAD needs
# min < max (ODB-0137 at floorplan otherwise). A kit with a signal cap below M5 carries its own two-layer
# CLOCK_RLAYERS (ref_tile.clock_rlayers); kits capped at M5+ leave the platform default alone.
CR=()
if [ -n "${CLOCK_RLAYERS:-}" ]; then
  read -r OT_CLK_LO OT_CLK_HI <<< "$CLOCK_RLAYERS"
  CR=(--orfs-var "MIN_CLK_ROUTING_LAYER=$OT_CLK_LO" --orfs-var "MAX_CLK_ROUTING_LAYER=$OT_CLK_HI")
fi
SO=(); [ -n "$STOP" ] && SO=(--pnr-stop-after $STOP)
# synthesis cap: unlimited for a route; the gate's floorplan smoke passes SYNTH_TIMEOUT (a SHARE stall fails in minutes)
STO=${SYNTH_TIMEOUT:-unlimited}
export OT_ORFS_NUM_CORES=${NC:-8} OT_SYNTH_TIMEOUT_SECONDS=$STO OT_FLOW_TIMEOUT_SECONDS=unlimited
export OT_MM_FF_SDC=${OT_MM_FF_SDC:-$K/signoff.sdc}
echo "$(date -Is) start $NAME kit=$K src=$(cat SOURCE_COMMIT 2>/dev/null) stop=$STOP" >> $W/STATUS
python3 tools/run_abi3_physical.py --view asap7 --top $TOP "${S[@]}" "${PARAMS[@]}" \
  --die-area 0 0 $FW $FH --core-area 2.16 2.16 $(python3 -c "print(round($FW-2.16,3), round($FH-2.16,3))") \
  "${PINS[@]}" $([ "${PINEX:-1}" = 1 ] && echo --pin-regions-exhaustive) "${EXTRA[@]}" \
  --routing-layers $RLAYERS "${CR[@]}" --clock-port $CLKPORT --clock-period-ns ${ROUTE_PERIOD_NS:-0.770} --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner ${CORNER:-WC} --hold-corners ${CORNER:-WC},BC --io-delay-fraction 0.2 --stages pnr \
  --place-density ${PD:-0.55} --hold-margin-ns ${HM:-0.010} --synth-timeout-seconds $STO --flow-timeout-seconds unlimited \
  --orfs-var NUM_CORES=${NC:-8} --orfs-var SDC_FILE=$KIT/clock.sdc --orfs-var QDM_SDC_DIR=$D \
  --orfs-var "PLACE_PINS_ARGS=-min_distance ${PIN_MIN_TRACKS:-2} -min_distance_in_tracks" \
  --orfs-var "IO_PLACER_H=$PIN_H" --orfs-var "IO_PLACER_V=$PIN_V" \
  --step-tcl PRE_CTS=$K/pre_cts.tcl --step-tcl POST_CTS=$(hook post_cts post_plain) \
  --step-tcl PRE_GLOBAL_ROUTE=$K/pre_grt.tcl --step-tcl POST_GLOBAL_ROUTE=$(hook post_grt post_plain) \
  --step-tcl PRE_DETAIL_ROUTE=$(hook pre_drt pre_ref_skew) --step-tcl POST_DETAIL_ROUTE=$K/post_drt.tcl \
  --step-tcl PRE_FILLCELL=$(hook pre_fill pre_ref_skew) --step-tcl POST_FILLCELL=$(hook post_fill post_plain) \
  --orfs-var "CTS_ARGS=${CTSA:--sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.75}" \
  --orfs-var OT_IO_SKEW=90 --orfs-var OT_IO_HOLD_SKEW=50 --orfs-var "OT_REF_GLOB=$REFGLOB" \
  --orfs-var "OT_IO_INTER=$INTER" --orfs-var OT_IO_SKEW_INTER=150 "${SO[@]}" \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag ref_$NAME \
  --keep-workdir $W/work --force --output $W/physical.json > $W/flow.log 2>&1
rc=$?
echo "flow_rc=$rc" > $W/status
[ -n "$STOP" ] && { echo "$(date -Is) stop-after $STOP rc=$rc" >> $W/STATUS; exit $rc; }
cp $K/signoff.sdc $W/signoff.sdc
python3 tools/w18/corner_sta_ref.py --orfs-dir $W/work/orfs --extra-sdc $W/signoff.sdc "${M[@]}" \
  --output $W/corner_sta.json > $W/sta.log 2>&1
src=$?
echo "corner_rc=$src" >> $W/status
echo "$(date -Is) done flow=$rc sta=$src" >> $W/STATUS
[ $rc -eq 0 ] && [ $src -eq 0 ]
