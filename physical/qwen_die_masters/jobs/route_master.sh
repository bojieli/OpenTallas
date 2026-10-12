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
PKV=()
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
# HOOK CHAIN (el1011-rm-pkfix 2026-10-11).  ORFS takes ONE file per hook (the last "export X_TCL" in config.mk wins), and
# this script owns PRE/POST_{CTS,GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}.  Before this, every other claimant was silently
# dropped: (1) a cfg's own EXTRA "--step-tcl PRE_GLOBAL_ROUTE=... / POST_DETAIL_ROUTE=..." (qfd_tile_lsl5's E-face
# stn_pin_keepout.tcl: 0 OT_PIN_KEEPOUT lines in its flow.log, rst_n DRT-0073 in the qfd_tile_nk_h3 parent), because this
# script's own --step-tcl came after EXTRA; (2) OT_RM_PK's keepout whenever PINKO was also set (merges fa7cba4c4 /
# 8d6275ef9, "PINKO wins").  Now every claimant is chained into one generated hook per step, in this order:
#   PRE_*  : this flow's base (pre_ref_skew / pre_cts_skew) -> PINKO add -> OT_RM_PK keepout -> the cfg's own hook(s)
#   POST_* : the cfg's own hook(s) -> OT_RM_PK keepout (removal) -> PINKO removal -> this flow's base (post_plain, last)
# Components are de-duplicated by file (stn_pin_keepout.tcl is a toggle: sourcing it twice in one hook would add then
# remove).  The wrappers pre_ref_skew_pk / post_plain_pk / pre_grt_pinko / post_drt_pinko are expanded into their parts.
# Every stn_pin_keepout.tcl chain runs ABOVE ONLY by default (preamble PIN-ACCESS KEEPOUT; OT_PK_ABOVE_ONLY=0 in the env or
# an explicit --orfs-var OT_PK_ABOVE_ONLY= in the cfg opts out).  PINKO (cfg or env) is above-only by construction.
# RM_DRYRUN=1 prints the resolved chain and the hook arguments, then exits before the flow.
QM=physical/qwen_die_masters; STN=physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
HOOKS=(PRE_CTS POST_CTS PRE_GLOBAL_ROUTE POST_GLOBAL_ROUTE PRE_DETAIL_ROUTE POST_DETAIL_ROUTE PRE_FILLCELL POST_FILLCELL)
declare -A HB=([PRE_CTS]=$QM/pre_cts_skew.tcl [POST_CTS]=$QM/post_plain.tcl [PRE_GLOBAL_ROUTE]=$QM/pre_ref_skew.tcl
  [POST_GLOBAL_ROUTE]=$QM/post_plain.tcl [PRE_DETAIL_ROUTE]=$QM/pre_ref_skew.tcl [POST_DETAIL_ROUTE]=$QM/post_plain.tcl
  [PRE_FILLCELL]=$QM/pre_ref_skew.tcl [POST_FILLCELL]=$QM/post_plain.tcl)
declare -A HK=() HC=()
_rm_expand() { case "${1#/src/}" in
  $QM/pre_ref_skew_pk.tcl) echo "$QM/pre_ref_skew.tcl $STN";; $QM/post_plain_pk.tcl) echo "$STN $QM/post_plain.tcl";;
  $QM/pre_grt_pinko.tcl) echo "$QM/pre_ref_skew.tcl $QM/pinko_add.tcl";; $QM/post_drt_pinko.tcl) echo "$QM/pinko_del.tcl $QM/post_plain.tcl";;
  *) echo "${1#/src/}";; esac; }
# (1) the cfg's own claims on a route-owned hook leave EXTRA and join the chain; every other EXTRA option passes as before
declare -p EXTRA >/dev/null 2>&1 || EXTRA=()
_X=(); _i=0; _n=${#EXTRA[@]}
while [ $_i -lt ${#EXTRA[@]} ]; do
  _a=${EXTRA[$_i]}
  _b=""; [ $((_i+1)) -lt $_n ] && _b=${EXTRA[$((_i+1))]}
  if [ "$_a" = --step-tcl ] && [ -n "$_b" ] && [ -n "${HB[${_b%%=*}]:-}" ]; then
    _h=${_b%%=*}; HC[$_h]="${HC[$_h]:-} $(_rm_expand "${_b#*=}")"; _i=$((_i+2)); continue
  fi
  _X+=("$_a"); _i=$((_i+1))
done
EXTRA=("${_X[@]}")
# (2) keepout knobs.  OT_RM_PK=1 (el1011-ds-misc/lint): stn_pin_keepout.tcl over the face-pin column; OT_PK_FRAC / OT_PK_HALO
# / OT_PK_FACES pass through only when the job sets them (the Tcl defaults are FRAC 0 / HALO 0.072 / all faces), so they
# no longer overwrite a cfg's own --orfs-var OT_PK_FRAC.  PINKO=1 (el1011-q-kvd): pinko_add / pinko_del.
PKPRE=""; PKPOST=""
[ "${PINKO:-0}" = 1 ] && PKPRE="$QM/pinko_add.tcl" && PKPOST="$QM/pinko_del.tcl"
if [ "${OT_RM_PK:-0}" = 1 ]; then
  PKPRE="$PKPRE $STN"; PKPOST="$STN $PKPOST"
  [ -n "${OT_PK_FRAC:-}" ] && PKV+=(--orfs-var "OT_PK_FRAC=$OT_PK_FRAC")
  [ -n "${OT_PK_HALO:-}" ] && PKV+=(--orfs-var "OT_PK_HALO=$OT_PK_HALO")
  [ -n "${OT_PK_FACES:-}" ] && PKV+=(--orfs-var "OT_PK_FACES=$OT_PK_FACES")
fi
mkdir -p $W/hooks; HARGS=()
for _h in "${HOOKS[@]}"; do
  if [ "${_h%%_*}" = PRE ]; then _l="${HB[$_h]}"; [ $_h = PRE_GLOBAL_ROUTE ] && _l="$_l $PKPRE"; _l="$_l ${HC[$_h]:-}"
  else _l="${HC[$_h]:-}"; [ $_h = POST_DETAIL_ROUTE ] && _l="$_l $PKPOST"; _l="$_l ${HB[$_h]}"; fi
  _u=(); for _c in $_l; do case " ${_u[*]:-} " in *" $_c "*) ;; *) _u+=("$_c");; esac; done
  # a lone base stays the plain file (unchanged hook name / sha for every job without extra claimants)
  for _c in "${_u[@]}"; do [ -f "$_c" ] || { echo "route_master: hook component $_c ($_h) missing" >&2; exit 2; }; done
  case " ${_u[*]} " in *" $STN "*) PKSTN=1;; esac
  if [ ${#_u[@]} -eq 1 ]; then HK[$_h]=${_u[0]}; else
    _f=$W/hooks/rm_chain_${_h,,}.tcl
    { echo "# route_master.sh hook chain for $_h (generated)"; echo "puts \"route_master chain $_h: ${_u[*]}\""
      for _c in "${_u[@]}"; do case "$_c" in /*) echo "source $_c";; *) echo "source /src/$_c";; esac; done; } > $_f
    HK[$_h]=$_f
  fi
  HARGS+=(--step-tcl "$_h=${HK[$_h]}")
done
if [ "${PKSTN:-0}" = 1 ]; then
  case " ${EXTRA[*]:-} " in
    *" OT_PK_ABOVE_ONLY="*) ;;
    *) PKV+=(--orfs-var "OT_PK_ABOVE_ONLY=${OT_PK_ABOVE_ONLY:-1}");;
  esac
fi
if [ "${RM_DRYRUN:-0}" = 1 ]; then
  for _h in "${HOOKS[@]}"; do
    if [ -f "${HK[$_h]}" ] && [ "${HK[$_h]#$W/}" != "${HK[$_h]}" ]; then echo "$_h = $(grep '^source' ${HK[$_h]} | sed 's#^source /src/##; s#^source ##' | tr '\n' ' ')"; else echo "$_h = ${HK[$_h]}"; fi
  done
  echo "PKV = ${PKV[*]:-}"; echo "EXTRA(after) = ${EXTRA[*]:-}"; exit 0
fi
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
  "${HARGS[@]}" \
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
