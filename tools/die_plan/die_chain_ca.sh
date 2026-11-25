#!/bin/bash
# KIT-OPS-6 11-15 (COORD): the die chains ALWAYS run the count-aligned (CA) steps.  proto_die.sh called die_sta_related without --count-align and
# qc_chain_s3r.sh exited before its CA section, so the legacy T/2 landed gate gave false landed failures on HEAD, KV and QC.
# usage: die_chain_ca.sh PROOF_DIR PLAN OUT_DIR [CLOCK_CELL=inv2] [extra die_sta_related args...]
#   (1) landed_phase_ocv  (2) count_align_plan  (3) count_align_bind  (4) die_sta_related --count-align BIND.json
# The die_sta_related run WITHOUT --count-align is kept as the LEGACY T/2 result (sta_legacy/, LEGACY label in CHAIN.log); it never gates.
set -u
PROOF=$1; PLAN=$2; OUT=$3; CC=${4:-inv2}; shift $(( $# > 3 ? 4 : $# ))
HERE=$(cd "$(dirname "$0")" && pwd); T=${CA_TOOLS:-$HERE}; H=$T/../s81_head
mkdir -p "$OUT"; log(){ echo "$1 $(date '+%F %T')" >> "$OUT/CHAIN.log"; }
rc=0
python3 -s "$H/landed_phase_ocv.py" "$PLAN" "$PROOF" --tools "$T" --clock-cell "$CC" --out "$OUT/landed_phase_ocv.json" > "$OUT/ca_ocv.log" 2>&1; r=$?; log "CA_OCV $r"; [ $r -ne 0 ] && rc=1
# S81-DIE-R3 11-17: a plan that declares the falling-edge ring write (clock.ring_hold.write_edge fall) is timed in that
# form (--ca-write-fall); without it the CA check times the rise-write form the die does not build (S81 D7w: -198.9 / 247
# fail rise-write vs +217.6 / 0 fail fall-write on the same bind)
# S81-CLOCK-WINDOW-1119: the snippet had lost its quotes (a Python SyntaxError hidden by 2>/dev/null), so every chain
# timed the rise-write form; single quotes keep it valid inside the bash double quotes.
WF=$(cd "$T" && python3 -I -c "import json,sys; sys.path.insert(0,'.'); import clock_landings as C; print('--ca-write-fall' if C.ring_write_fall(json.load(open(sys.argv[1]))) else '')" "$PLAN" 2>/dev/null)
# S81-CLOCK-WINDOW-1119: a fall-write plan is also PLANNED (K/DEPTH for lag L + T/2) and BOUND (verify window +T/2)
# in that form; without it the plan picks rise-write K and the gate fails the guard (S81 cw6: 136 hi -304 ps).
WFP=; WFB=; [ -n "$WF" ] && { WFP="--write-fall-plan $PLAN"; WFB="--plan-die $PLAN"; }
# KV-CROSSING-1119 11-20 (COORD): the fall chain plans at --max-depth 16 unless CA_PLAN_ARGS names a depth: a fall write
# needs a window the depth-8 ring does not hold on long start-tree paths (KV pcsink: 26 crossings with no K/DEPTH at 8).
MD=; [ -n "$WF" ] && case " ${CA_PLAN_ARGS:-} " in *" --max-depth "*) ;; *) MD="--max-depth 16";; esac
# Use the same die count frame for planning and binding unless the caller
# supplied the frame (directly or through the count-align STA plan).
FRAME=(--frame-plan "$PLAN")
case " ${CA_PLAN_ARGS:-} " in
  *" --frame-plan "*|*" --frame-plan="*|*" --sta-plan "*|*" --sta-plan="*) FRAME=() ;;
esac
python3 -s "$T/count_align_plan.py" "$OUT/landed_phase_ocv.json" ${CA_PLAN_ARGS:-} "${FRAME[@]}" $WFP $MD --out "$OUT/count_align_plan.json" > "$OUT/ca_plan.log" 2>&1; r=$?; log "CA_PLAN $r"; [ $r -ne 0 ] && rc=1
python3 -s "$T/count_align_bind.py" "$OUT/count_align_plan.json" ${CA_BIND_ARGS:-} $WFB --out "$OUT/count_align_bind.json" > "$OUT/ca_bind.log" 2>&1; r=$?; log "CA_BIND $r"; [ $r -ne 0 ] && rc=1
log "CA_WRITE_EDGE ${WF:-rise}"
# REAL-VIEWS-1119 (COORD 11-19): every signed core view (--core-view) and signed type view (--kit) whose pins match this
# plan goes to die_sta_related, so hold is MEASURED on those pairs; unsigned / pin-mismatched blocks stay on the contract
# (reasons in real_views/real_views.json).  Store: REAL_VIEWS_STORE (rec_<die>.json = counter signed records,
# digest_<die>.json = signed-export digest, default ~/.local/state/real-views); REAL_VIEWS=0 turns it off.
rv_resolve(){ # RVTOOLS PLAN OUTDIR -> RVA (args) + RVMSG; never fails the chain (no view = contract)
  RVA=(); RVMSG="REAL_VIEWS off"; [ "${REAL_VIEWS:-1}" = 0 ] && return 0
  if python3 -I "$1/real_views.py" "$2" --out "$3" --store "${REAL_VIEWS_STORE:-$HOME/.local/state/real-views}" \
      ${REAL_VIEWS_FETCH:+--fetch} > "$3.log" 2>&1; then mapfile -t RVA < "$3/args.txt"; RVMSG="REAL_VIEWS $(tail -n 1 "$3.log")"
  else RVMSG="REAL_VIEWS FAILED (see $3.log): contract only"; fi
}
# --kit needs a die_sta_related with the kit register fallback (kit_model reg=); older tool copies get the core views only
rv_for(){ # STA_TOOLS -> RVF (RVA filtered for that die_sta_related)
  local x k=1 r=1; RVF=()
  grep -q "def kit_model(spec, corner, name, reg" "$1/die_sta_related.py" 2>/dev/null || { k=0; RVMSG="$RVMSG | kits SKIPPED for $1 (no kit register fallback)"; }
  grep -q -e "--related-pairs" "$1/die_sta_related.py" 2>/dev/null || r=0
  for x in "${RVA[@]}"; do case $x in --kit=*) [ $k = 1 ] && RVF+=("$x");; --related-pairs=*) [ $r = 1 ] && RVF+=("$x");; *) RVF+=("$x");; esac; done
}
RVF=()
if [ "${REAL_VIEWS_GIVEN:-0}" = 1 ]; then log "REAL_VIEWS passed by caller"
else rt=$T; [ -f "$rt/real_views.py" ] || rt=$HERE; rv_resolve "$rt" "$PLAN" "$OUT/real_views"; rv_for "$T"; log "$RVMSG"; fi
if [ $rc -eq 0 ]; then
  ( cd "$T" && python3 -s die_sta_related.py "$PROOF" --plan "$PLAN" --out "$OUT/sta_ca" --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell "$CC" \
      --count-align "$OUT/count_align_bind.json" --count-align-key part $WF "${RVF[@]}" "$@" ) > "$OUT/sta_ca.log" 2>&1
  r=$?
  log "STA_CA $r"
  if [ "$r" -eq 0 ]; then
    # measured vs contract hold per pair class (CONTRACT = declared/kit-contract window; MEASURED = both endpoints real views)
    python3 -I "$HERE/real_views.py" report "$OUT/sta_ca" > "$OUT/hold_report.log" 2>&1
    while read -r l; do log "$l"; done < "$OUT/hold_report.log"
  else
    rc=$r
  fi
else log "STA_CA SKIPPED (a CA step failed: the legacy result below is NOT a landed verdict)"; fi
( cd "$T" && python3 -s die_sta_related.py "$PROOF" --plan "$PLAN" --out "$OUT/sta_legacy" --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell "$CC" "${RVF[@]}" "$@" ) > "$OUT/sta_legacy.log" 2>&1
log "STA_LEGACY $? (LEGACY T/2 landed result: informational only, not the landed gate)"
exit $rc
