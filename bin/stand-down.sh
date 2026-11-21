#!/bin/bash
# usage: stand-down.sh LANE SUCCESSOR ["note"] [--handed UNIT_OR_NAME,...]      (FLOW-PROC-B 11-21, FABLE-FLOW-0800 class b)
# The ONLY writer of lanes/LANE-STATUS.tsv stood-down rows.  Schema: tools/lane_status.py (lane, status, successor, updated, note; one row per lane).
#   SUCCESSOR is a lane name, or the word none (then the note must say who looks at the lane's work).
# Refuses when (1) a name or schema problem, (2) SUCCESSOR's own chain leads back to LANE, (3) LANE still has registered RUNNING ot-run / ot-push records
# (~/.local/state/ot-status, pid alive, lane = LANE) on any host that its handoff (lanes/handoff/LANE.md) does not name by unit, record name or pid, and that
# --handed does not list.  A host that does not answer within 20 s is reported and does not block (set STAND_HOSTS to change the host list).
# Writes the row, posts "STAND-DOWN [LANE -> SUCCESSOR]" under LANE's own name (no redirect), and commits both through bin/post.sh in ONE coord-commit.
set -eu
C=${COORD_DIR:-/home/ubuntu/coord}
[ $# -ge 2 ] || { sed -n 2,3p "$0" >&2; exit 2; }
lane=$1; succ=$2; shift 2
note=""; handed=""
while [ $# -gt 0 ]; do case "$1" in --handed) handed=${2:-}; shift 2;; *) note="$1"; shift;; esac; done
re='^[A-Za-z0-9][A-Za-z0-9._-]*$'
[[ "$lane" =~ $re ]] || { echo "stand-down: bad lane name '$lane'" >&2; exit 2; }
[[ "$succ" =~ $re ]] || { echo "stand-down: bad successor '$succ' (a lane name or none)" >&2; exit 2; }
[ "$lane" != "$succ" ] || { echo "stand-down: successor is the lane itself" >&2; exit 2; }
[ "$succ" != none ] || [ -n "$note" ] || { echo "stand-down: successor none needs a note saying who reads the lane's work" >&2; exit 2; }
LS="$C/tools/lane_status.py"; T="$C/lanes/LANE-STATUS.tsv"
exec 8>"$C/.stand-down.lock"; flock -w 120 8 || { echo "stand-down: lock busy" >&2; exit 1; }
# (2) a chain from SUCCESSOR that returns to LANE
if [ "$succ" != none ]; then
  python3 -I - "$T" "$lane" "$succ" <<'PY' || { echo "stand-down: successor $succ already leads back to $lane (cycle)" >&2; exit 1; }
import sys
sys.path.insert(0, sys.argv[1].rsplit("/lanes/", 1)[0] + "/tools")
import post_redirect as P
st = P.load_status(sys.argv[1].rsplit("/lanes/", 1)[0])
st[sys.argv[2]] = ("stood-down", sys.argv[3], "")
sys.exit(1 if sys.argv[2] in P.resolve(sys.argv[3], st) else 0)
PY
fi
# (3) registered running PIDs of the lane that the handoff does not name
me=$(hostname | cut -d. -f1); hosts=${STAND_HOSTS:-"intel1 intel2 epyc2 epyc4 epyc7 epyc8 epyc9 epyc10 epyc11 epyc12"}
hf="$C/lanes/handoff/$lane.md"; refuse=""
for h in $me $hosts; do
  [ "$h" = "$me" ] && [ "${seen:-}" = 1 ] && continue
  if [ "$h" = "$me" ]; then seen=1; out=$(python3 -I "$LS" --running "$lane" 2>&1) || out="";
  else out=$(timeout 20 ssh -o BatchMode=yes -o ControlPath=none -o ConnectTimeout=8 "$h" python3 -I - --running "$lane" < "$LS" 2>/dev/null) || { echo "stand-down: host $h did not answer; not checked" >&2; continue; }; fi
  while IFS= read -r j; do
    [ -n "$j" ] || continue
    ok=0
    for k in $(python3 -I -c 'import json,sys; r=json.loads(sys.argv[1]); print(" ".join(str(r.get(x) or "") for x in ("name","unit","pid")))' "$j"); do
      [ -n "$k" ] || continue
      { [ -f "$hf" ] && grep -qF -- "$k" "$hf"; } && ok=1
      case ",$handed," in *",$k,"*) ok=1;; esac
    done
    [ $ok = 1 ] || refuse="$refuse
  $h: $j"
  done <<< "$out"
done
if [ -n "$refuse" ]; then
  echo "stand-down: REFUSED, $lane still has running registered jobs its handoff does not name:$refuse" >&2
  echo "  Name each unit/record name in lanes/handoff/$lane.md (successor owns it) or pass --handed NAME,NAME, then run again." >&2
  exit 1
fi
res=$(python3 -I "$LS" --set "$T" "$lane" "$succ" "$note") || { echo "stand-down: schema check failed, nothing written" >&2; exit 1; }
new=$(mktemp "$C/lanes/.LANE-STATUS.XXXXXX")
printf '%s\n' "$res" > "$new"
mv -f "$new" "$T"
POST_NO_RESOLVE=1 bash "$C/bin/post.sh" "$lane" "STAND-DOWN [$lane -> $succ] stood down; successor $succ.${note:+ $note} (row in lanes/LANE-STATUS.tsv; posts to $lane now redirect)" lanes/LANE-STATUS.tsv
