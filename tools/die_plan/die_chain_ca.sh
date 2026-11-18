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
python3 -s "$T/count_align_plan.py" "$OUT/landed_phase_ocv.json" ${CA_PLAN_ARGS:-} --out "$OUT/count_align_plan.json" > "$OUT/ca_plan.log" 2>&1; r=$?; log "CA_PLAN $r"; [ $r -ne 0 ] && rc=1
python3 -s "$T/count_align_bind.py" "$OUT/count_align_plan.json" ${CA_BIND_ARGS:-} --out "$OUT/count_align_bind.json" > "$OUT/ca_bind.log" 2>&1; r=$?; log "CA_BIND $r"; [ $r -ne 0 ] && rc=1
# S81-DIE-R3 11-17: a plan that declares the falling-edge ring write (clock.ring_hold.write_edge fall) is timed in that
# form (--ca-write-fall); without it the CA check times the rise-write form the die does not build (S81 D7w: -198.9 / 247
# fail rise-write vs +217.6 / 0 fail fall-write on the same bind)
WF=$(cd "$T" && python3 -I -c "import json,sys; sys.path.insert(0,.); import clock_landings as C; print(--ca-write-fall if C.ring_write_fall(json.load(open(sys.argv[1]))) else )" "$PLAN" 2>/dev/null)
log "CA_WRITE_EDGE ${WF:-rise}"
if [ $rc -eq 0 ]; then
  ( cd "$T" && python3 -s die_sta_related.py "$PROOF" --plan "$PLAN" --out "$OUT/sta_ca" --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell "$CC" \
      --count-align "$OUT/count_align_bind.json" --count-align-key part $WF "$@" ) > "$OUT/sta_ca.log" 2>&1; log "STA_CA $?"
else log "STA_CA SKIPPED (a CA step failed: the legacy result below is NOT a landed verdict)"; fi
( cd "$T" && python3 -s die_sta_related.py "$PROOF" --plan "$PLAN" --out "$OUT/sta_legacy" --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell "$CC" "$@" ) > "$OUT/sta_legacy.log" 2>&1
log "STA_LEGACY $? (LEGACY T/2 landed result: informational only, not the landed gate)"
exit $rc
