#!/bin/bash
# Generic margin route of one Qwen ROM r21 die master (closure-loop stage command).  Per-master settings come from
# physical/qwen_die_masters/cfg/<CFG>.env (TOP, SRCS, PARAMS[], FW, FH, PINS[], INTER, REFGLOB, PD, MACROS[], EXTRA[],
# NC, STAGES).  Route over-constrained at 770 ps; sign-off at the real 833.333 ps (60 / 25 ps uncertainty): the
# sign-off SDC re-creates core_clk at 833.333, sets the propagated clock and applies the die-context boundary
# (io_ref_skew.sdc: 0.2 T outside budget, referenced to this block's measured boundary-register clock arrival, plus
# 90 ps same-region / 150 ps on the INTER ports (die wire to another clock region), hold allowance 50 ps).
# usage: route_master.sh CFG LABEL OUTROOT [cts]      (SRC = source snapshot root; HM route hold margin, ns)
# PIN_H / PIN_V (env or cfg, drive-2140 2026-10-08, reviewer DQ1/DQ2): pin layers for the IO placer, e.g. PIN_H='M4 M6'
# PIN_V='M5 M7' spreads a dense face over two layers (fp-lint pin density is per layer); unset = ORFS default (M4 / M5).
set -uo pipefail
CFG=$1; NAME=$2; OUT=$3; STOP=${4:-}
SRC=${SRC:?}; W=$OUT/$NAME; mkdir -p $W; cd $SRC
D=/src/physical/qwen_die_masters
source physical/qwen_die_masters/cfg/$CFG.env
# drive-1143: a macro view lives only inside the ORFS image, so run_abi3_physical refuses host synth with
# --macro-view / --memory-macro ("run --stages pnr"); any cfg naming one routes with STAGES=pnr.
case " ${EXTRA[*]:-} " in *" --macro-view "*|*" --memory-macro "*) STAGES=pnr;; esac
S=(); for f in $SRCS; do S+=(--source $f); done
M=(); for m in "${MACROS[@]}"; do M+=(--macro $m); done
SO=()
PL=()
[ -n "${PIN_H:-}" ] && PL+=(--orfs-var "IO_PLACER_H=$PIN_H")
[ -n "${PIN_V:-}" ] && PL+=(--orfs-var "IO_PLACER_V=$PIN_V")
[ -n "$STOP" ] && SO=(--pnr-stop-after $STOP)
export OT_ORFS_NUM_CORES=${NC:-16} OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
# FLOW-HOLD (2026-10-07): with OT_ROUTE_HOLD_CORNERS=mm the FF scene re-derives this die-context boundary at FF
export OT_MM_FF_SDC=${OT_MM_FF_SDC:-physical/qwen_die_masters/io_ref_skew.sdc}
echo "$(date -Is) start $NAME cfg=$CFG src=$(cat SOURCE_COMMIT 2>/dev/null) stop=$STOP" >> $W/STATUS
python3 tools/run_abi3_physical.py --view asap7 --top $TOP "${S[@]}" "${PARAMS[@]}" \
  --die-area 0 0 $FW $FH --core-area 2.16 2.16 $(python3 -c "print(round($FW-2.16,3), round($FH-2.16,3))") \
  "${PINS[@]}" ${PINS:+--pin-regions-exhaustive} "${EXTRA[@]}" \
  --routing-layers ${RLAYERS:-M2 M7} --clock-port ${CLKPORT:-clk} --clock-period-ns 0.770 --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner ${CORNER:-WC} --hold-corners ${CORNER:-WC},BC --io-delay-fraction 0.2 --stages ${STAGES:-synth,pnr} \
  --place-density ${PD:-0.55} --hold-margin-ns ${HM:-0.010} --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=${NC:-16} --orfs-var SDC_FILE=${QDMD:-$D}/${SDCF:-die_p770.sdc} --orfs-var QDM_SDC_DIR=${QDMD:-$D} \
  --orfs-var 'PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks' "${PL[@]}" \
  --step-tcl PRE_CTS=physical/qwen_die_masters/pre_cts_skew.tcl --step-tcl POST_CTS=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_GLOBAL_ROUTE=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_GLOBAL_ROUTE=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_DETAIL_ROUTE=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_DETAIL_ROUTE=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_FILLCELL=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_FILLCELL=physical/qwen_die_masters/post_plain.tcl \
  --orfs-var "CTS_ARGS=${CTSA:--sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.75}" \
  --orfs-var OT_IO_SKEW=90 --orfs-var OT_IO_HOLD_SKEW=50 --orfs-var "OT_REF_GLOB=$REFGLOB" \
  --orfs-var "OT_IO_INTER=$INTER" --orfs-var OT_IO_SKEW_INTER=150 "${SO[@]}" \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag qdm_$NAME \
  --keep-workdir $W/work --force --output $W/physical.json > $W/flow.log 2>&1
rc=$?
echo "flow_rc=$rc" > $W/status
[ -n "$STOP" ] && { echo "$(date -Is) stop-after $STOP rc=$rc" >> $W/STATUS; exit $rc; }
# sign-off SDC at 833.333 with this master's boundary settings bound (the STA container gets no environment)
if [ -f physical/qwen_die_masters/signoff/$CFG.sdc ]; then cp physical/qwen_die_masters/signoff/$CFG.sdc $W/signoff.sdc; else python3 physical/qwen_die_masters/jobs/signoff_sdc.py $CFG > $W/signoff.sdc; fi
python3 tools/w18/corner_sta_ref.py --orfs-dir $W/work/orfs --extra-sdc $W/signoff.sdc "${M[@]}" \
  --output $W/corner_sta.json > $W/sta.log 2>&1
src=$?
echo "corner_rc=$src" >> $W/status
echo "$(date -Is) done flow=$rc sta=$src" >> $W/STATUS
[ $rc -eq 0 ] && [ $src -eq 0 ]
