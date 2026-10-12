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
# struct-close 2026-10-09 (fill-5 F5-5): a PD / NC exported by the job overrides the cfg's (the cfg used to overwrite them
# silently: hgi_mtp_accept18 gave the same route at PD 0.40 / 0.44 / 0.48).
OT_ENV_PD=${PD:-}; OT_ENV_NC=${NC:-}
source physical/qwen_die_masters/cfg/$CFG.env
[ -n "$OT_ENV_PD" ] && PD=$OT_ENV_PD; [ -n "$OT_ENV_NC" ] && NC=$OT_ENV_NC
# el1011-ds-misc/lint (2026-10-11): hard-child abstract fixes for tools/hier_contract/child_lint.py, job-env opt-ins
# (defaults = the flow as before).  OT_RM_PK=1 chains the face-pin keepout physical/hbm_accel_die_views/stations/bench/
# stn_pin_keepout.tcl (the pin_access_pregrt.tcl recipe, bf0080873: the two layers adjacent to each face's pin layer are
# obstructed over the face-pin column before GRT and removed again after DRT; OT_PK_FRAC / OT_PK_HALO / OT_PK_FACES pass
# through) onto this flow's own PRE_GLOBAL_ROUTE / POST_DETAIL_ROUTE hooks (a second --step-tcl for the same hook would
# replace them).  OT_RM_CORE_Y = core inset on the S/N faces (default 2.16): the M7 PG stripes span the core, so a thin
# tile (38.88 um: 34.56 / 38.88 = 89%) misses lint (b)'s 90% full-length stripe rule at the 2.16 inset.  OT_RM_XARGS =
# extra run_abi3_physical options appended last (last --orfs-var wins).
CIY=${OT_RM_CORE_Y:-2.16}
GRT_PRE=physical/qwen_die_masters/pre_ref_skew.tcl; DRT_POST=physical/qwen_die_masters/post_plain.tcl; PKV=()
if [ "${OT_RM_PK:-0}" = 1 ]; then
  GRT_PRE=physical/qwen_die_masters/pre_ref_skew_pk.tcl; DRT_POST=physical/qwen_die_masters/post_plain_pk.tcl
  PKV=(--orfs-var OT_PK_FRAC=${OT_PK_FRAC:-0} --orfs-var OT_PK_HALO=${OT_PK_HALO:-0.072})
  [ -n "${OT_PK_FACES:-}" ] && PKV+=(--orfs-var "OT_PK_FACES=$OT_PK_FACES")
fi
XA=(${OT_RM_XARGS:-})
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
# Routing layers (main 10-11): an explicit RLAYERS wins; otherwise a --routing-layers in the kit's extra options is honoured;
# only then the M2 M7 default. Before this, the default was appended after EXTRA and silently overrode a kit's M2 M6.
RL=(--routing-layers ${RLAYERS:-M2 M7})
if [ -z "${RLAYERS:-}" ]; then for _a in "${EXTRA[@]}"; do [ "$_a" = "--routing-layers" ] && RL=(); done; fi
echo "$(date -Is) start $NAME cfg=$CFG src=$(cat SOURCE_COMMIT 2>/dev/null) stop=$STOP" >> $W/STATUS
python3 tools/run_abi3_physical.py --view asap7 --top $TOP "${S[@]}" "${PARAMS[@]}" \
  --die-area 0 0 $FW $FH --core-area 2.16 $CIY $(python3 -c "print(round($FW-2.16,3), round($FH-$CIY,3))") \
  "${PINS[@]}" ${PINS:+--pin-regions-exhaustive} "${EXTRA[@]}" \
  "${RL[@]}" --clock-port ${CLKPORT:-clk} --clock-period-ns ${ROUTE_PERIOD_NS:-0.770} --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner ${CORNER:-WC} --hold-corners ${CORNER:-WC},BC --io-delay-fraction 0.2 --stages ${STAGES:-synth,pnr} \
  --place-density ${PD:-0.55} --hold-margin-ns ${HM:-0.010} --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=${NC:-16} --orfs-var SDC_FILE=${QDMD:-$D}/${SDCF:-die_p770.sdc} --orfs-var QDM_SDC_DIR=${QDMD:-$D} \
  --orfs-var "PLACE_PINS_ARGS=-min_distance ${PIN_MIN_TRACKS:-1} -min_distance_in_tracks" "${PL[@]}" \
  --step-tcl PRE_CTS=physical/qwen_die_masters/pre_cts_skew.tcl --step-tcl POST_CTS=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_GLOBAL_ROUTE=$GRT_PRE --step-tcl POST_GLOBAL_ROUTE=physical/qwen_die_masters/post_plain.tcl \
  --step-tcl PRE_DETAIL_ROUTE=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_DETAIL_ROUTE=$DRT_POST \
  --step-tcl PRE_FILLCELL=physical/qwen_die_masters/pre_ref_skew.tcl --step-tcl POST_FILLCELL=physical/qwen_die_masters/post_plain.tcl \
  --orfs-var "CTS_ARGS=${CTSA:--sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.75}" \
  --orfs-var OT_IO_SKEW=90 --orfs-var OT_IO_HOLD_SKEW=50 --orfs-var "OT_REF_GLOB=$REFGLOB" \
  --orfs-var "OT_IO_INTER=$INTER" --orfs-var OT_IO_SKEW_INTER=150 "${SO[@]}" \
  --slew-margin-percent 30 --purpose signoff_target --nickname-tag qdm_$NAME \
  "${PKV[@]}" "${XA[@]}" --keep-workdir $W/work --force --output $W/physical.json > $W/flow.log 2>&1
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
