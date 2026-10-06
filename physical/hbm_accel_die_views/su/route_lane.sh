#!/bin/bash
# CLAUDE HBM-ABSTRACTS (hub): re-harden a CLOSED hub lane element (unchanged RTL) in a die-dense footprint with every
# pin on the left edge (mirrored columns in the quarter face a shared channel).  r2 recipe (default): signals M2-M5,
# pins M4 on every track (a light lane's 2,251 pins need 2,251 of the 3,375 M4 tracks of its 162 um edge; the
# platform's 2-track spacing gives 1,672 slots), PDN top M6 (su/pdn_lane_m6.tcl) so M6 / M7 over the lane stay open to the quarter and the quarter's M7
# stripes feed the lane; r1 (MAXL=M7 PINL="M4 M6" PDN=common/pdn_view.tcl) blocks every quarter layer over a lane.
# SS60/FF25 at 0.833 ns, IO false-pathed (register-direct, checked after the route), corner STA.
#   route_lane.sh <label> <top> <W> <H> [run_abi3_physical args]   env: R (scratch base), SRC (snapshot dir, default src0), SRCS, KEEP, CORES, NEED, MAXL, PINL, PDN, PPA, IOC, CP (route clock ns; < 0.833 over-constrains, sign-off re-time at 833 in corner_sta_833.json)
R=${R:?}; lab=$1; top=$2; W_=$3; H_=$4; shift 4
W=$R/routes/$lab; mkdir -p $W; cd $R/${SRC:-src0}
export OT_ORFS_NUM_CORES=${CORES:-8} NUM_CORES=${CORES:-8} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
echo "$top $W_ $H_ $SRCS $*" > $W/args; cat SOURCE_COMMIT > $W/SOURCE_COMMIT
S=""; for s in $SRCS; do S="$S --source $s"; done
/srv/opentallas-scratch/admit.sh ${NEED:-12} -- python3 tools/run_abi3_physical.py --view asap7 --top $top $S "$@" \
  --clock-period-ns ${CP:-0.833} --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages pnr \
  --die-area 0 0 $W_ $H_ --core-area 0 0.54 $W_ $(python3 -c "print(round($H_-0.54,3))") --orfs-var IO_CONSTRAINTS=/src/physical/hbm_accel_die_views/su/${IOC:-io_left.tcl} --routing-layers M2 ${MAXL:-M5} --orfs-var "IO_PLACER_H=${PINL:-M4}" \
  --orfs-var "PLACE_PINS_ARGS=${PPA:--min_distance 1 -min_distance_in_tracks}" \
  --orfs-var PDN_TCL=/src/physical/hbm_accel_die_views/${PDN:-su/pdn_lane_m6.tcl} \
  --place-density ${PD:-0.65} --hold-margin-ns ${HM:-0.01} --orfs-var ADDER_MAP_FILE= \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag hub_$lab \
  ${KEEP:+--orfs-var "SYNTH_KEEP_MODULES=$KEEP"} \
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --keep-workdir $W/work --force --output $W/physical.json > $W/run.log 2>&1
echo "rc=$?" > $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --output $W/corner_sta.json > $W/corner.log 2>&1
echo "corner_rc=$?" >> $W/exit
python3 tools/w18/corner_sta.py --orfs-dir $W/work/orfs --post-sdc physical/hbm_accel_die_views/su/signoff833_clk.sdc --output $W/corner_sta_833.json > $W/corner833.log 2>&1
python3 physical/hbm_accel_die_views/su/outcheck.py $W/work/orfs > $W/outcheck.txt 2>&1
echo "post_rc=$?" >> $W/exit
# lane view (LEF + SS/FF ETM) with the interface constraints of Carson's adopted real SU lane view (ot_su12_full, same
# lane clock / IO budget), not a second interface definition
python3 tools/hbm_fmax_attn_abstract.py --orfs-dir $W/work/orfs --name $top --out $W/view --tmp-dir $W/abs_tmp \
  --interface-sdc physical/hbm_die_abstracts_20261006/compute/ot_su12_full/interface.sdc > $W/export.log 2>&1
echo "export_rc=$?" >> $W/exit
