#!/bin/bash
# TOK-S81-1 10-28 (COORD 20:10 (6)): S81 strict bind of the CURRENT die plan with the existing alignment checks wired in,
# every check's log kept in OUT (attach OUT/summary.txt to every S81 bind READY).  Run it through ot-run (elab ~35 min /
# <=48 GB, bind ~35 min); never on localhost.
#   bind_s81_current.sh PLAN.json OUT
# env: MANIFEST (default the PD7d manifest), REUSE_ELAB=1 (keep OUT/out/asbuilt.json from an earlier run of the SAME
#      manifest + tree), CA_LPO + CA_FLAGS (count_align_bind input from the die clock flow: landed_phase_ocv json and the
#      --sta-* flags of that flow), CA_SKIP="<reason>" (records the CA check as NOT RUN; the summary verdict is then
#      INCOMPLETE, never PASS).
# Checks, in order (each fails closed):
#   1 FRAME_LK  per-frame landing K of every u_f_* frame == results/s81_unblock3_1027/fi_seam/frame_lk.json (check_frame_lk.py)
#   2 BIND      tools/die_plan/bind.py elab + bind --strict (0 errors, tied 0, unbound 0, undriven 0, multiply 0)
#   3 LATENCY   gen.py latency on PLAN rebased on the bind's bind_latency.json (the table the composer prices)
#   4 CA        tools/die_plan/count_align_bind.py on the plan's count-aligned crossings (needs the clock flow input)
set -u
P=$(realpath "$1"); O=$(realpath -m "$2"); mkdir -p "$O"
W=$(git -C "$(dirname "$(realpath "$0")")" rev-parse --show-toplevel); cd "$W"
M=${MANIFEST:-physical/die_plan/s81/bind/asbuilt_b178_coll_pd7d.json}
S=$O/summary.txt; : > "$S"
say() { echo "$*" | tee -a "$S"; }
say "TOK-S81 BIND $(date) tree $(git rev-parse --short=10 HEAD) plan $(sha256sum "$P" | cut -c1-12) manifest $M ($(sha256sum "$M" | cut -c1-12))"
v=PASS
B=physical/die_plan/s81/bind
python3 -I $B/check_frame_lk.py $B/inputs/die_b178.v $B/models/s81_asb_models.sv \
    results/s81_unblock3_1027/fi_seam/frame_lk.json --out "$O/frame_lk_check.json" > "$O/frame_lk.log" 2>&1
r=$?; say "1 FRAME_LK rc=$r $(head -1 "$O/frame_lk.log")"; [ $r = 0 ] || v=FAIL
if [ "${REUSE_ELAB:-0}" = 1 ] && [ -s "$O/out/asbuilt.json" ]; then
  say "2a ELAB reused $O/out/asbuilt.json"
else
  python3 -I tools/die_plan/bind.py elab "$P" --asbuilt "$M" --out "$O/out" --mem 48 > "$O/elab.log" 2>&1
  r=$?; say "2a ELAB rc=$r $(date)"; [ $r = 0 ] || { say "VERDICT FAIL (elab)"; exit 1; }
fi
python3 -I tools/die_plan/bind.py bind "$P" --asbuilt "$M" --out "$O/out" --strict > "$O/bind.log" 2>&1
r=$?; say "2b BIND --strict rc=$r $(date) $(tail -1 "$O/bind.log" | cut -c1-300)"; [ $r = 0 ] || v=FAIL
if [ -s "$O/out/bind_latency.json" ]; then
  python3 -I tools/die_plan/gen.py latency "$P" --rebase-bind "$O/out/bind_latency.json" --out "$O/lat" > "$O/lat.log" 2>&1
  r=$?; say "3 LATENCY rc=$r $(tail -1 "$O/lat.log" | cut -c1-200)"; [ $r = 0 ] || v=FAIL
else
  say "3 LATENCY NOT RUN (no bind_latency.json)"; v=FAIL
fi
if [ -n "${CA_LPO:-}" ]; then
  # shellcheck disable=SC2086
  python3 -I tools/die_plan/count_align_bind.py "$CA_LPO" --from-ocv --parts ocv --scale 1.0 --samples 2000 ${CA_FLAGS:-} \
      --out "$O/ca_bind.json" > "$O/ca_bind.log" 2>&1
  r=$?; say "4 CA count_align_bind rc=$r $(tail -1 "$O/ca_bind.log" | cut -c1-200)"; [ $r = 0 ] || v=FAIL
else
  say "4 CA NOT RUN: ${CA_SKIP:-no CA_LPO given}"; [ "$v" = PASS ] && v=INCOMPLETE
fi
say "VERDICT $v $(date)"
[ "$v" = PASS ] && exit 0
[ "$v" = INCOMPLETE ] && exit 3
exit 1
