#!/usr/bin/env bash
# TOK-FUNC-HBM (10-21): ONE command for the HBM d4g release die functional token pass (HBM-DeepSeek TOK.HDS + HBM-Qwen
# TOK.HQ, single user): assemble the die RTL -> SW quadrant slice -> per-layer + chained replays -> build -> run -> report.
#
#   MODE=source (default, grade "RTL-functional (source assembly)"):
#     CONTRACT = the release die's source contract (pre-relay: relays are physical) at SRC_REV; the l12 bank-latency
#     layer (tools/hbm_die_v16/d4g_layers/l12_banklat.py of SRC_REV) is applied so every fixed-latency VM client gets
#     its compiler budget (pads fill the short lanes: the static schedule is the one the post-relay die runs), then
#     contract_die_v.py emits die.v.  OVERLAY="path[@rev] ..." replaces bundle files by another revision's (pending RTL
#     the release source needs; default empty. Historical r14 needs an explicit per-bank RD_LAT ctlx overlay).
#   MODE=gen_rtl (GEN-composed RTL only, source children): DIE_V=<GEN die.v of record> CONTRACT=<its contract>
#     SRC_REV=<its source rev>; no l12 (already in the GEN contract), no overlay unless given.
#
#   env: OUT (local work dir) SRC_REV CONTRACT [DIE_V] [L12_OVERLAY] [OVERLAY] [REPLAYS] [MEM=256] [JOBS=48]
#        [STAGE_HOSTS="ot-gold1 ot-gold2"] (data staged there; ot-run unpinned picks among hosts that have it)
#        [PRIO=die] (ot-run --priority die for the BUILD: die-netlist / release token gate builds; 10-22 STEWARD-HBMc)
#        [RUN=1] (0 = assemble + emit only)
#   Emission: DS L0/L2/L14 (layer_images, fixtures FIX_DS=<dir with L00 L02 L14>) and Qwen L0 + L0->L1 chain ranks 0/5
#   (qwen_layer_images emit, operands QOP=<dir with operands_{L0,chain}.npz>), SU native READ/WRITE_RETURN read from
#   the contract's su_SW0 (the die's own parameters).  Writes OUT/report.json (+ OUT/log/*).
set -u -o pipefail
T=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$T/../.." && pwd)
REPO=${REPO:-/home/ubuntu/OpenTallas}
MODE=${MODE:-source}
# TOK-FUNC3-HBM (10-21): CLI hooks.  --die-netlist <GEN die.v> = closure rerun of this SAME script (MODE=gen_rtl,
#   DIE_V=<die.v>; CONTRACT/SRC_REV must name the post-relay contract and its exact commit).  --reuse = run frozen
#   replay sets on an EXISTING slice binary (no re-assembly, no rebuild; see REUSE below).
while [ $# -gt 0 ]; do case "$1" in
  --die-netlist) MODE=gen_rtl; DIE_V=${2:?--die-netlist <GEN die.v>}; shift 2;;
  --reuse) REUSE=1; shift;;
  *) echo "unknown arg $1" >&2; exit 2;;
esac; done
# REUSE=1: FROZEN=<dir with replay/<set>/ + emit/ (or <set>.json) + tb_slice.sv + slice.v> [EXTRA_SETS="<replay dir>:<json dir> ..."
#   run INSTEAD of same-name frozen sets, e.g. the Qwen --safe-calendar packet] [ONLY="set ..."]
#   BIN_HOST=<host> BIN_ROOT=<remote root holding out/obj/Vtb_hbm_slice + slice/{tb_slice.sv,slice.v}> [BOUNDARY=<boundary.json>]
#   The frozen TB/slice must be byte-identical to the binary's (fail closed); replays run in a separate run root on
#   BIN_HOST (RUNROOT, symlinked out/obj, the binary root is never written), then the same report (per-layer, chain,
#   token rungs with measured stream/serial/HBM cycles).
if [ "${REUSE:-0}" = 1 ]; then
  T=$(cd "$(dirname "$0")" && pwd)
  OUT=${OUT:?OUT}; FROZEN=${FROZEN:?FROZEN}; BIN_HOST=${BIN_HOST:?BIN_HOST}; BIN_ROOT=${BIN_ROOT:?BIN_ROOT}
  SRC_REV=${SRC_REV:?SRC_REV (provenance of the binary)}; CONTRACT=${CONTRACT:?CONTRACT}
  TAG=${TAG:-$(basename "$OUT")}; RUNROOT=${RUNROOT:-/srv/opentallas-scratch/claude/tok-func3-hbm/$TAG}
  # Canonicalise on the execution host: existing parent symlinks must not hide
  # an overlap that lets staging or the out/obj link modify the binary tree.
  printf -v REUSE_GUARD 'python3 - %q %q' "$BIN_ROOT" "$RUNROOT"
  timeout 300 ssh "$BIN_HOST" "$REUSE_GUARD" <<'PY_GUARD' || exit 4
import os, sys
binary, run = (os.path.realpath(p) for p in sys.argv[1:])
if os.path.commonpath((binary, run)) in (binary, run):
    print(f"REUSE_PATH_OVERLAP binary={binary} run={run}", file=sys.stderr)
    sys.exit(4)
print(f"REUSE_PATH_DISJOINT binary={binary} run={run}")
PY_GUARD
  mkdir -p "$OUT/log" "$OUT/rj" "$OUT/stage/slice/replay"; L=$OUT/log
  say() { echo "$(date -Is) $*" | tee -a "$L/summary.log"; }
  timeout 300 ssh "$BIN_HOST" "test -x $BIN_ROOT/out/obj/Vtb_hbm_slice" || { say "NO_BINARY $BIN_HOST:$BIN_ROOT"; exit 4; }
  want=$(cd "$FROZEN" && sha256sum tb_slice.sv slice.v | awk '{print $1}' | tr '\n' ' ')
  have=$(timeout 300 ssh "$BIN_HOST" "cd $BIN_ROOT/slice && sha256sum tb_slice.sv slice.v" | awk '{print $1}' | tr '\n' ' ')
  [ "$want" = "$have" ] || { say "TB_MISMATCH frozen=[$want] binary=[$have]"; exit 4; }
  BINSHA=$(timeout 600 ssh "$BIN_HOST" "sha256sum $BIN_ROOT/out/obj/Vtb_hbm_slice" | cut -d' ' -f1)
  say "REUSE binary=$BIN_HOST:$BIN_ROOT sha256=$BINSHA tb+slice identical [$want]"
  cp "$FROZEN/tb_slice.sv" "$FROZEN/slice.v" "$OUT/stage/slice/"; cp "${BOUNDARY:-$FROZEN/boundary.json}" "$OUT/stage/slice/boundary.json" || exit 2
  cp "$T/check_slice_run.py" "$OUT/stage/"
  NAMES=()
  addset() { # $1 replay dir, $2 dir with <name>.json (rj) or emit/
    local rd=$1 jd=$2 n
    for d in "$rd"/*/; do n=$(basename "$d"); [ -f "$d/hdr.mem" ] || continue
      case " ${NAMES[*]} " in *" $n "*) say "KEEP $n (EXTRA_SETS override; frozen copy not run)"; continue;; esac
      if [ -f "$jd/$n.json" ]; then cp "$jd/$n.json" "$OUT/rj/$n.json"
      else local l=${n%%_x*}; local x=${n#"$l"}; local e="$jd/emit/$l/replay${x}.json"; if [ -f "$e" ]; then cp "$e" "$OUT/rj/$n.json"; else cp "$d/index.json" "$OUT/rj/$n.json" || return 2; say "RJ_FROM_INDEX $n"; fi; fi
      NAMES+=("$n"); rsync -a --delete "$d" "$OUT/stage/slice/replay/$n/"; done; }
  for xs in ${EXTRA_SETS:-}; do addset "${xs%%:*}" "${xs#*:}" || exit 2; done   # first: they replace same-name frozen sets
  addset "$FROZEN/replay" "$FROZEN" || exit 2
  [ -z "${ONLY:-}" ] || NAMES=($ONLY)
  timeout 600 ssh "$BIN_HOST" "mkdir -p $RUNROOT/out && ln -sfn $BIN_ROOT/out/obj $RUNROOT/out/obj" || exit 2
  timeout 1800 rsync -a "$OUT/stage/" "$BIN_HOST:$RUNROOT/" || exit 2
  say "STAGED ${#NAMES[@]} sets -> $BIN_HOST:$RUNROOT"
  REMOTE="$RUNROOT" RDIR=slice/replay HOST="$BIN_HOST" OUT="$OUT" PAR="${RUN_PAR:-8}" RUN_MEM="${RUN_MEM:-64}" \
    bash "$T/run_pay_replays.sh" "${NAMES[@]}"; SIM_RC=$?
  python3 "$T/tok_func_hbm_report.py" --out "$OUT" --mode "${MODE:-source}" --rev "$SRC_REV" --contract "$CONTRACT" \
    --binary "$BIN_HOST:$BIN_ROOT/out/obj/Vtb_hbm_slice" --binary-sha256 "$BINSHA" "${NAMES[@]}"; RRC=$?
  say "DONE reuse sim_rc=$SIM_RC report_rc=$RRC report=$OUT/report.json"
  exit "$RRC"
fi
case "$MODE" in
  source|gen_rtl) ;;
  *) echo "MODE=$MODE unsupported: mapped-netlist qualification requires frozen mapped hierarchy and libraries; use gen_rtl for GEN composition with source children" >&2; exit 2;;
esac
OUT=${OUT:?OUT}; SRC_REV=${SRC_REV:?SRC_REV}; CONTRACT=${CONTRACT:?CONTRACT}
FIX_DS=${FIX_DS:?FIX_DS (dir with L00 L02 L14 fixtures: records.json operands.npz images/)}
QOP=${QOP:?QOP (dir with operands_L0.npz operands_chain.npz from qwen_layer_images snap)}
MEM=${MEM:-256}; JOBS=${JOBS:-48}; RUN=${RUN:-1}
CONNECTED_LOWERING=${CONNECTED_LOWERING:-0}
CONNECTED_ARGS=(); HC_ARGS=(); CUT_ARGS=()
# SM_LOWERING=1 (TOK-FUNC2-HBM-SM 10-21, opt-in): SM.MATVEC records drive the slice's real SM chain (sm_slice_lower.py);
#   SMW=<ds_sm_weights root with L00 L02 L14>, SM_KV=<qwen_sm_mv_kv root with L0/ chain/> (Qwen rank 0).  Each lowered
#   record set is its own component replay (ds_l<L>_sm, qw_<stage>_r0_sm_L<L>_<tag>) with its own calendar reservation.
SM_LOWERING=${SM_LOWERING:-0}; SM_ARGS=(); QSM_ARGS=()
if [ "$SM_LOWERING" = 1 ]; then
  SM_ARGS=(--sm-lowering --smw "${SMW:?SMW (ds_sm_weights root)}")
  [ -n "${SM_KV:-}" ] && QSM_ARGS=(--sm-kv "$SM_KV")
fi
# TOK-FUNC2-HBM-SU: production SU lowerings by record profile (layer_images --su-lower2). Token runs (CONNECTED_LOWERING=1)
# use it by default: every su_record-based record gets the safe-calendar reader/drain contract (absent roles read A's
# own bank -- pgslice.sv:303 -- and the drain samples one edge after the lane write). Plain --safe-calendar refuses
# every record outside its single tested A->O profile (ValueError), so it cannot be the layer emission.
SU_LOWER2=${SU_LOWER2:-$CONNECTED_LOWERING}
if [ "$CONNECTED_LOWERING" = 1 ]; then
  CONNECTED_ARGS=(--connected-lowering --side-source "$OUT/bundle/rtl/hbm_accel/die_glue/scoped_d4g/pgslice.sv")
  HC_ARGS=(--connected-hc --checkpoint "${HC_CHECKPOINT:-$HOME/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277}")
  CUT_ARGS=(--include "^(hc_eng|hleaf_SE|sucore_(SW|SE|NW|NE)|stl_(SW|SE|NW|NE)|stu_(SW|SE|NW|NE)_[0-9]{2}|std_(SW|SE|NW|NE)_[0-9]{2}[ab]|str_C)$")
fi
# TOK-FUNC2-HBM-CX: CX=1 (default with CONNECTED_LOWERING=1) emits the DS layers with the COLL/HC components CONNECTED
# inside the layer compile (layer_images --cx, cx_layer_1021.py): shared VM placement, SU programmes split at every
# component, alternating finite SU owner-0 calendar epochs / component CP epochs, producer-cone parts.  Those replays
# carry their own calendar epochs (no reserve-component) and replace the relocated PAY probes (RUN_PAY defaults to 0).
# CX_IDX=1 also connects IDX.TOPK (route.top6) -- that needs hb_idx__ctl INSIDE the cut: new slice.v / TB build.
CX=${CX:-$CONNECTED_LOWERING}; CX_IDX=${CX_IDX:-0}
[ "$CX" = 1 ] && TB_NEV_MIN=${TB_NEV_MIN:-${PAY_NEV:-11651}}
CX_L14=${CX_L14:-"--cx-chapters 75 --cx-skip 64"}   # L14: quarter VM capacity (engram) -> VM chapter + eg_kv standalone
if [ "$CX_IDX" = 1 ] && [ "$CONNECTED_LOWERING" = 1 ]; then
  CUT_ARGS=(--include "^(hc_eng|hleaf_SE|sucore_(SW|SE|NW|NE)|stl_(SW|SE|NW|NE)|stu_(SW|SE|NW|NE)_[0-9]{2}|std_(SW|SE|NW|NE)_[0-9]{2}[ab]|str_C|hb_idx__ctl)$")
fi
STAGE_HOSTS=${STAGE_HOSTS:-"ot-gold1 ot-gold2"}
OVERLAY=${OVERLAY-} # current coherent source defaults to no moving-main overlays
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC_REV=$(git -C "$REPO" rev-parse --verify "$SRC_REV^{commit}") || exit 2
TAG=${TAG:-$(basename "$OUT")}
REMOTE=${REMOTE:-/srv/opentallas-scratch/claude/tok-func-hbm/$TAG}
mkdir -p "$OUT/log"; L=$OUT/log
say() { echo "$(date -Is) $*" | tee -a "$L/summary.log"; }
SRCWT=$OUT/srcwt                       # read-only export of SRC_REV tools (l12 / contract_die_v / functional bind)
if [ ! -d "$SRCWT/tools/hbm_die_v16" ]; then
  mkdir -p "$SRCWT"; git -C "$REPO" archive "$SRC_REV" tools/hbm_die_v16 tools/die_port_bind.py results/arch/hbm_die_d4g/gen0/die.v.pads.json | tar -x -C "$SRCWT" || exit 2
fi
say "TOK_FUNC_HBM mode=$MODE src=$SRC_REV contract=$CONTRACT ($(sha256sum "$CONTRACT" | cut -c1-16)) tools=$(git -C "$ROOT" rev-parse --short=9 HEAD)"

# 1. die RTL assembly ------------------------------------------------------------------------------------------------
if [ "$MODE" = source ]; then
  L12O=${L12_OVERLAY:-results/arch/hbm_die_d4g/gen2e4r11_1020/l12_budget_r11.json}
  OVA=(); if [ -n "$L12O" ]; then git -C "$REPO" show "$SRC_REV:$L12O" > "$OUT/l12_overlay.json" 2>/dev/null || cp "$L12O" "$OUT/l12_overlay.json"; OVA=(--budget-overlay "$OUT/l12_overlay.json"); fi
  (cd "$SRCWT" && python3 tools/hbm_die_v16/d4g_layers/l12_banklat.py "$CONTRACT" "$OUT/contract_func.json" --report "$OUT/l12.json" "${OVA[@]}" ${L12_ARGS:-}) > "$L/l12.log" 2>&1 \
    || { say "L12_FAIL"; tail -5 "$L/l12.log"; exit 3; }
  say "$(tail -1 "$L/l12.log")"
  FC=$OUT/contract_func.json
  (cd "$SRCWT" && python3 tools/hbm_die_v16/contract_die_v.py emit "$FC" "$OUT/die.v") > "$L/die_v.log" 2>&1 || { say DIE_V_FAIL; exit 3; }
  (cd "$SRCWT" && python3 tools/hbm_die_v16/d4g_functional_bind.py "$FC" --report "$OUT/functional_bind.json") > "$L/functional_bind.log" 2>&1
  say "$(tail -1 "$L/functional_bind.log")"
  grep -q "^FUNCTIONAL_BIND PASS" "$L/functional_bind.log" || exit 3
  DIEV=$OUT/die.v
else
  FC=$CONTRACT; DIEV=${DIE_V:?DIE_V (GEN die.v) for MODE=gen_rtl}
fi
python3 "$T/die_filelist.py" --contract "$FC" --repo "$REPO" --rev "$SRC_REV" --out "$OUT/fl" > "$L/filelist.log" 2>&1 || { say FILELIST_FAIL; exit 3; }; say "$(tail -1 "$L/filelist.log")"
# Functional compilation consumes source configuration, not closed physical views.
# The only define-bearing current master is unchanged from the r14 source configuration.
VIEWS=${VIEWS:-}
if [ -z "$VIEWS" ]; then
  VIEWS=$OUT/source_compile_defines.json
  python3 - "$VIEWS" "$FC" <<'PYDEFS'
import json, sys
contract = json.load(open(sys.argv[2]))
params = [i.get("params", {}) for i in contract["instances"].values() if i["master"] == "ot_hbm_accel_smh_attn"]
assert params and all(p == params[0] for p in params), "SMH instances need distinct parameter-specialized unit vehicles"
json.dump({"ot_hbm_accel_smh_attn": {"env": "DEFINES=OT_SMH_FC_HIER,OT_SMH_HIER,OT_SMH_XLK,OT_FP_DATA_NORST,OT_SMH_DRST0,OT_SMH_RSTRELAY", "params": params[0]}}, open(sys.argv[1], "w"), indent=2)
PYDEFS
fi
VA=(--views "$VIEWS")
python3 "$T/make_bundle.py" --fl "$OUT/fl" --repo "$REPO" --rev "$SRC_REV" --die "$DIEV" --wt "$ROOT" --out "$OUT/bundle" "${VA[@]}" > "$L/bundle.log" 2>&1 || { say BUNDLE_FAIL; exit 3; }
for o in $OVERLAY; do f=${o%@*}; r=${o#*@}; [ "$r" = "$o" ] && r=origin/main
  git -C "$REPO" show "$r:$f" > "$OUT/bundle/$f" || { say "OVERLAY_FAIL $o"; exit 3; }
  say "OVERLAY $f <- $r $(git -C "$REPO" rev-parse "$r") sha256=$(sha256sum "$OUT/bundle/$f" | cut -d' ' -f1)"; done
cp "$T/check_slice_run.py" "$OUT/bundle/"
[ "${HIERWRAP:-0}" = 1 ] && cp "$T/hier_param_wrap.py" "$T/run_slice_vehicle.sh" "$OUT/bundle/"

# 2. SW quadrant slice (input pads/relays pulled in: the die's own lane latency in front of the slice) --------------
RLX=${RELAY_RE:-'^(l12p_|rf\d+_)'}
python3 "$T/cut_slice.py" --die "$DIEV" --contract "$FC" --set sw --with-relays "$RLX" "${CUT_ARGS[@]}" --out "$OUT/bundle/slice" > "$L/cut.log" 2>&1 || { say CUT_FAIL; exit 3; }
say "$(grep -m1 '^SLICE' "$L/cut.log")"

# 3. replays (compiler of record on the die's own SU timing) ----------------------------------------------------------
read RR WR RFL < <(python3 -c "import json,sys; p=json.load(open(sys.argv[1]))['instances']['su_SW0']['params']; print(p['READ_RETURN'], p['WRITE_RETURN'], p.get('RF_LOCAL', 0))" "$FC")
SU2_ARGS=(); [ "$SU_LOWER2" = 1 ] && SU2_ARGS=(--su-lower2 --rf-local "$RFL" --nev "${PAY_NEV:-11651}")
say "SU native timing READ_RETURN=$RR WRITE_RETURN=$WR (contract su_SW0)"
B=$OUT/bundle/slice/boundary.json; RJ=$OUT/rj; mkdir -p "$RJ"
CXR=""
# TOKg 10-23: COLL_TRANSPORT=1 -> COLL gathers on the die's own lane timing (coll_transport.py: launch lane + far-end
# ingress lanes traced in die.v); default 0 = GEN2 schedule until a full rec2 PASS on an equal-depth landing die.
if [ "${COLL_TRANSPORT:-0}" = 1 ]; then
  (cd "$ROOT" && PYTHONPATH=tools python3 -m hbm_layer_vehicle.coll_transport --contract "$FC" --die-v "$DIEV" --out "$OUT/coll_transport.json") > "$L/coll_transport.log" 2>&1 || { say COLL_TRANSPORT_FAIL; exit 3; }
  say "COLL_TRANSPORT $(tail -1 "$L/coll_transport.log")"
fi
PV_ARGS=()
[ "${PV_PROBABILITY_CANDIDATE:-0}" != 1 ] || PV_ARGS=(--pv-probability-candidate --pv-probability-source "$OUT/bundle" --pv-probability-contract "$FC")
for LL in 00 02 14; do l=$((10#$LL))
  CXA=(); if [ "$CX" = 1 ]; then CXA=(--cx --cx-contract "$FC" --cx-l12 "$OUT/l12.json" --cx-checkpoint "${HC_CHECKPOINT:-$HOME/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277}" --cx-ops "COLL,HC$([ "$CX_IDX" = 1 ] && echo ,IDX)"); [ "${COLL_TRANSPORT:-0}" = 1 ] && CXA+=(--cx-coll-transport "$OUT/coll_transport.json"); [ "$l" = 14 ] && CXA+=($CX_L14); fi
  (cd "$ROOT" && python3 tools/hbm_layer_vehicle/layer_images.py --design ds --layer $l --programme "$FIX_DS/L$LL/images/ds_v41_1M_L${LL}_per_die.json" \
     --fixtures "$FIX_DS/L$LL" --boundary "$B" "${CONNECTED_ARGS[@]}" "${SU2_ARGS[@]}" --native-read-return $RR --native-write-return $WR "${CXA[@]}" "${SM_ARGS[@]}" "${PV_ARGS[@]}" --out "$OUT/emit/ds_l$l") > "$L/emit_ds_l$l.log" 2>&1 \
    || { say "EMIT_FAIL ds_l$l"; exit 3; }; cp "$OUT/emit/ds_l$l/replay.json" "$RJ/ds_l$l.json"; say "EMIT ds_l$l $(tail -c 260 "$L/emit_ds_l$l.log" | tr -d '\n')"
  for xp in "$OUT/emit/ds_l$l/replay_x"[0-9]*.json; do [ -f "$xp" ] || continue   # SU_LOWER2 independent parts (NEV fit)
    xn=$(basename "$xp" .json); cp "$xp" "$RJ/ds_l${l}_${xn#replay_}.json"; SU2_EXTRA="${SU2_EXTRA:-} ds_l${l}_${xn#replay_}"
    [ "$CX" = 1 ] && CXR="$CXR ds_l${l}_${xn#replay_}"; done
  [ "$CX" = 1 ] && CXR="$CXR ds_l$l"
done
for st in L0 chain; do
  QSAFE_ARGS=(); [ "${QW_SAFE_CALENDAR:-$CONNECTED_LOWERING}" != 1 ] || QSAFE_ARGS=(--safe-calendar)
  (cd "$ROOT" && python3 tools/hbm_layer_vehicle/qwen_layer_images.py emit --stage $st --ranks 0,5 --boundary "$B" --operands "$QOP/operands_$st.npz" \
     --native-read-return $RR --native-write-return $WR "${QSAFE_ARGS[@]}" "${QSM_ARGS[@]}" --out "$OUT/qemit") > "$L/emit_qw_$st.log" 2>&1 || { say "EMIT_FAIL qw_$st"; exit 3; }
  for r in 0 5; do [ -f "$OUT/qemit/$st/r$r/replay.json" ] && cp "$OUT/qemit/$st/r$r/replay.json" "$RJ/qw_${st,,}_r$r.json"; done
  say "EMIT qw_$st $(grep -o '"counts": {[^}]*}' "$L/emit_qw_$st.log" | head -1)"
done
REPLAYS=${REPLAYS:-"ds_l0 ds_l2 ds_l14 qw_l0_r0 qw_l0_r5 qw_chain_r0 qw_chain_r5${SU2_EXTRA:-}"}
# The isolated SU probe must own the bank on every request/write-return edge.
# This explicit reservation is component-only; it does not qualify a production layer calendar.
for n in $REPLAYS; do
  case " $CXR " in *" $n "*) continue;; esac          # CX parts carry their own SU/component calendar epochs
  python3 "$T/native_su_calendar.py" reserve-component "$RJ/$n.json" "$B" "$RJ/$n.calendar.json" > "$L/calendar_$n.log" 2>&1 \
    || { say "CALENDAR_FAIL $n"; exit 3; }
  mv "$RJ/$n.calendar.json" "$RJ/$n.json"
done
if [ "$SM_LOWERING" = 1 ]; then
  for l in 0 2 14; do cp "$OUT/emit/ds_l$l/sm/replay.json" "$RJ/ds_l${l}_sm.json"; REPLAYS="$REPLAYS ds_l${l}_sm"; done
  for st in L0 chain; do for d in "$OUT/qemit/$st/r0"/sm_L*; do [ -f "$d/replay.json" ] || continue
    n="qw_${st,,}_r0_$(basename "$d")"; cp "$d/replay.json" "$RJ/$n.json"; REPLAYS="$REPLAYS $n"; done; done
  say "SM_LOWERING replays: $(echo $REPLAYS | tr ' ' '\n' | grep -c _sm)"
fi
# Existing real HC/COLL payloads share the same source contract and static VM
# ownership epochs. These remain relocated component probes: HC far-end root
# results and COLL peer inputs retain explicit fixture provenance.
RUN_PAY=${RUN_PAY:-$([ "$CX" = 1 ] && echo 0 || echo 1)}
if [ "$RUN_PAY" = 1 ]; then
  PAY_L12_ARGS=(); [ ! -f "${PAY_L12:-$OUT/l12.json}" ] || PAY_L12_ARGS=(--l12 "${PAY_L12:-$OUT/l12.json}")
  [ "${COLL_TRANSPORT:-0}" = 1 ] && PAY_L12_ARGS+=(--coll-transport "$OUT/coll_transport.json")
  for LL in 00 02 14; do
    l=$((10#$LL))
    python3 "$T/merge_layer_replay.py" --shared-calendar "${HC_ARGS[@]}" \
      --su "$OUT/emit/ds_l$l/replay.json" --su-manifest "$OUT/emit/ds_l$l/manifest.json" \
      --fixtures "$FIX_DS/L$LL" --contract "$FC" "${PAY_L12_ARGS[@]}" \
      --boundary "$B" --nev "${PAY_NEV:-11651}" --out "$OUT/pay" --name "ds_l${l}_pay" \
      > "$L/pay_ds_l$l.log" 2>&1 || { say "PAY_EMIT_FAIL ds_l$l"; exit 3; }
    for rp in "$OUT/pay/ds_l${l}_pay_p"[0-9]*.json; do
      cp "$rp" "$RJ/"
      REPLAYS="$REPLAYS $(basename "$rp" .json)"
    done
    say "PAY ds_l$l $(tail -1 "$L/pay_ds_l$l.log") shared_static_epochs=1 connected_data=0"
  done
fi
NEV=$(python3 -c "import json,sys; print(max(16, ${TB_NEV_MIN:-0}, 1 + max(sum(e['k']!='M' for e in json.load(open(f))['events']) for f in sys.argv[1:])))" $(for n in $REPLAYS; do echo "$RJ/$n.json"; done))
python3 "$T/gen_slice_tb.py" --boundary "$B" --out "$OUT/bundle/slice" --nev "$NEV" $(for n in $REPLAYS; do echo --replay "$RJ/$n.json"; done) > "$L/tb.log" 2>&1 || { say TB_FAIL; cat "$L/tb.log"; exit 3; }
say "$(tail -1 "$L/tb.log")"
[ "$RUN" = 1 ] || { say "ASSEMBLED (RUN=0)"; exit 0; }

# Optional current-source attention/index leg of the same entrypoint. Staged job
# scripts preserve shell variables; the driver includes all originally required
# DS L0/L2/L14 full+s32, Qwen L0/chain, TOPK/n12, and dependent SU merge cases.
# Use RUN_ATT=1 for that coverage; positive component results never imply a full token.
if [ "${RUN_ATT:-0}" = 1 ]; then
  SRC_REV="$SRC_REV" LOGD="$OUT/att/log" bash "$T/run_att14.sh" \
    "${ATT_BENCH_REV:-cf2b071fdc8874526640746288eee68248c16fa7}" "$OUT/bundle" \
    "$REMOTE/att" "${ATT_STAGE_HOST:-${STAGE_HOSTS%% *}}" > "$L/att_driver.log" 2>&1 &
  ATT_PID=$!
  say "ATT driver_pid=$ATT_PID log=$L/att_driver.log"
fi

# 4. stage + build + run (fleet, unpinned) ---------------------------------------------------------------------------
for h in $STAGE_HOSTS; do timeout 600 ssh "$h" "mkdir -p $REMOTE" && timeout 1800 rsync -a --delete "$OUT/bundle/" "$h:$REMOTE/" && say "STAGED $h:$REMOTE"; done
/home/ubuntu/bin/ot-run ${PRIO:+--priority $PRIO} --mem "$MEM" --threads "$JOBS" --disk 200 --dir "$REMOTE" -- env SRC="$REMOTE" OUT="$REMOTE/out" JOBS="$JOBS" HIERWRAP="${HIERWRAP:-0}" BUILD_ONLY=1 bash run_slice_vehicle.sh > "$L/build.log" 2>&1
BRC=$?; H=$(grep -o 'RAN on [a-z0-9-]*' "$L/build.log" | tail -1 | awk '{print $3}'); say "BUILD rc=$BRC host=$H"
[ -n "$H" ] && timeout 120 ssh "$H" "test -x $REMOTE/out/obj/Vtb_hbm_slice" || { say NO_BINARY; exit 4; }
ATT_RC=0
if [ -n "${ATT_PID:-}" ]; then
  wait "$ATT_PID" || ATT_RC=$?
  say "ATT rc=$ATT_RC log=$L/att_driver.log"
fi
REMOTE="$REMOTE" RDIR=slice/replay HOST="$H" OUT="$OUT" PAR="${RUN_PAR:-8}" \
  RUN_MEM="${RUN_MEM:-64}" bash "$T/run_pay_replays.sh" $REPLAYS
SIM_RC=$?
python3 "$T/tok_func_hbm_report.py" --out "$OUT" --mode "$MODE" --rev "$SRC_REV" --contract "$CONTRACT" $REPLAYS
RRC=$?
[ "$ATT_RC" = 0 ] && [ "$SIM_RC" = 0 ] || RRC=1
say "DONE replay_rc=$RRC report=$OUT/report.json token=INCOMPLETE"
exit "$RRC"
