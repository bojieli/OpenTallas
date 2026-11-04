#!/bin/bash
# GRT183-RESUME for kit runners (FLOW-28 2026-11-04, DIE-HBM-63/FORMS hand form on fused_host_program): the runner's make
# command runs through this wrapper inside the kit's container.  Default on; OT_GRT183_RESUME=0 at the runner, or
# 'export OT_GRT183_RESUME = 0' in config.mk, opts out.
#   grt183_make.sh CMD...   CMD = make ... | bash /work/kwrs_make.sh RS make ...
# Class: full GRT reaches 0 overflow, then the incremental route inside repair_design / repair_timing dies with GRT-0183.
# In the same process neither -end_incremental nor a new full route recovers; a fresh process from the resized design does.
# grt183_resume.tcl (ROOT 10-15, unchanged, sourced before the kit's PRE_GLOBAL_ROUTE hook) saves that design and re-raises.
# Then this wrapper runs CMD exactly once more, with 4_cts.odb = the saved design; every repair runs again.  Nothing else:
#   - no saved design (GRT-0183 in the first full route, any other failure): rc as before, no re-run.  A re-run of an
#     unchanged design would repeat the same route.
#   - second GRT-0183: the hook sees the marker 5_1_grt.grt183_recovered.json and refuses; rc as before.
#   - no gate, guard, margin or repair changes.  4_cts.odb is swapped by rename only, so a stage-resume hardlink to the
#     previous attempt is never written through, and the original CTS database (mtime included) comes back afterwards.
W=${OT_GRT183_WORK:-/work}
S=${OT_GRT183_SCRIPTS:-/OpenROAD-flow-scripts/flow/scripts}/global_route.tcl
HOOK="source /work/grt183_resume.tcl"
case " $* " in *" print-"*) exec "$@";; esac
if [ "${OT_GRT183_RESUME:-1}" = 0 ] || grep -q '^export OT_GRT183_RESUME = 0' "$W/config.mk" 2>/dev/null || [ ! -f "$W/grt183_resume.tcl" ]; then exec "$@"; fi
# disposable container copy of the ORFS script, as orfs_hold_mm.py: hook first, then the kit's own (also an 'override' one)
if ! grep -qF "$HOOK" "$S" 2>/dev/null; then
  if ! grep -q '^ *source_step_tcl PRE GLOBAL_ROUTE' "$S" 2>/dev/null; then echo "OT_GRT183_RESUME inactive: no PRE GLOBAL_ROUTE step in $S"; exec "$@"; fi
  sed -i "s|^\( *\)source_step_tcl PRE GLOBAL_ROUTE|\1$HOOK\n&|" "$S"
fi
export KWRS_DONE=${KWRS_DONE:-$W/.kwrs_done.$PPID}   # kwrs_make.sh keeps the runner's own done list under this wrapper
R=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1)
restore() { if [ -n "$R" ] && [ -f "$R/4_cts.pre_grt183.odb" ]; then mv -f "$R/4_cts.pre_grt183.odb" "$R/4_cts.odb"; fi; }
restore   # a re-run killed hard left the swap in place; its marker stays, so it does not get another one
"$@"; rc=$?
[ "$rc" != 0 ] || exit 0
R=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1)
[ -n "$R" ] || exit "$rc"
L=$(ls -d "$W"/run/logs/asap7/*/base 2>/dev/null | head -1)
G=$L/5_1_grt.log
if [ -f "$R/5_1_grt.grt183_recovered.json" ] || [ ! -f "$R/5_1_grt.grt183_resume.odb" ] || [ ! -f "$R/4_cts.odb" ] \
  || ! grep -q OT_GRT183_RESUME_SAVED "$G" 2>/dev/null || ! grep -q GRT-0183 "$G"; then exit "$rc"; fi
cp -p "$G" "$G.grt183_attempt1"
python3 -I - "$R" "$G" "$rc" > "$R/5_1_grt.grt183_recovered.json" <<'PY'
import hashlib, json, sys
R, G, rc = sys.argv[1:]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()
lines = [l.rstrip() for l in open(G, errors="replace") if "GRT-0183" in l or "OT_GRT183_RESUME_SAVED" in l][:6]
print(json.dumps({"schema": "opentallas.grt183_resume.v1", "by": "grt183_make.sh", "rc_attempt1": int(rc),
                  "attempt1_log": "5_1_grt.log.grt183_attempt1", "attempt1_lines": lines,
                  "cts_odb_sha256": sha(R + "/4_cts.odb"), "resume_odb_sha256": sha(R + "/5_1_grt.grt183_resume.odb")}, indent=1))
PY
mv "$R/4_cts.odb" "$R/4_cts.pre_grt183.odb" && mv "$R/5_1_grt.grt183_resume.odb" "$R/4_cts.odb" || { restore; exit "$rc"; }
trap restore EXIT
[ ! -f "$KWRS_DONE" ] || sed -i '/^do-grt$/d;/^do-5_1/d' "$KWRS_DONE"
echo "OT_GRT183_RESUME attempt 1 rc $rc: re-running once in a fresh process from the resized design $(date -u '+%F %T')"
"$@"; rc=$?
echo "OT_GRT183_RESUME attempt 2 rc $rc $(date -u '+%F %T')"
exit "$rc"
