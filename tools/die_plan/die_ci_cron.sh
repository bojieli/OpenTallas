#!/bin/bash
# DIE-CI scheduler (lane DIE-CI 2026-10-24; runs on localhost = the hub, from systemd user timers):
#   die_ci_cron.sh commit    hourly timer: run only if main moved AND the new commits touch tools/die_plan or
#                            physical/die_plan (G2 re-runs only for dies whose plan / G2 tools changed; else CARRIED)
#   die_ci_cron.sh nightly   nightly timer: full run (G2 on every die) on main, whether or not anything changed
# Flow: pick a scratch2 host with ot-run --pick -> fetch main + detached CI worktree there -> stage the registered
# partition views -> ot-run die_ci.py run on that host -> rsync the run back to localhost -> commit the JSON/MD to
# branch claude/die-ci-results (pushed) -> keep the "DIE-CI LATEST:" line of ~/coord/HANDOFF.md current.
# Never touches ~/OpenTallas beyond reading refs; serialised by flock.
set -uo pipefail
MODE=${1:-commit}
export PATH=$HOME/.local/bin:$HOME/.local/opentallas-tools/bin:$PATH
HUB=$HOME/OpenTallas
TOOLS=${DIE_CI_TOOLS:-$HUB/tools/die_plan}          # die_ci.py + views registry used on localhost
STATE=$HOME/.local/state/die-ci
LR=${DIE_CI_LOCAL_ROOT:-/srv/opentallas-scratch/claude/die-ci}   # localhost results + logs
R=${DIE_CI_RUN_ROOT:-/srv/opentallas-scratch2/claude/die-ci}      # run root on the scratch2 hosts (owner: never root disks)
RESW=${DIE_CI_RESULTS_WT:-$HOME/wt/die-ci-results}                # results branch worktree (localhost)
RESB=claude/die-ci-results
HANDOFF=${DIE_CI_HANDOFF:-$HOME/coord/HANDOFF.md}
STA_REF=${DIE_CI_STA_REF:-claude/die-sta-1024}      # die_sta.py source while it is not on main (lane DIE-STA)
# memory: one ot-run job PER DIE, sized by `die_ci.py job-mem <die>` (its largest G2 docker + 8 GB); G2 part probes
# killed by their cgroup (EXIT 137) re-run at 2x inside the job up to the die's ceiling (die_ci.DIES g2_mem)
# DIECI_WD_1101 (COORD 11-01 19:0x, FLOW-21; the 10-27 nightly held epyc2 for 5 days): a run stops itself
#   - after DIE_CI_MAX_H (12) hours wall time,
#   - when no file under its run dir on the run host was written for DIE_CI_IDLE_MIN (120) minutes while a per-die job
#     has started (the 2-h hung-job watchdog rule, OWNER 12.22: log mtime is the progress signal),
#   - when a newer nightly starts (it SIGTERMs the older run of any mode and takes the lock).
# Stopping = SIGTERM the run's own ot-run clients, `systemctl --user stop` the ot-heavy scopes named in its per-die logs,
# and `docker stop` the G2 containers that mount its run dir on the run host (exact handles only, never pkill).
MAX_S=${DIE_CI_MAX_S:-$(( ${DIE_CI_MAX_H:-12} * 3600 ))}
IDLE_S=${DIE_CI_IDLE_S:-$(( ${DIE_CI_IDLE_MIN:-120} * 60 ))}
POLL_S=${DIE_CI_POLL_S:-60}
T0=$(date +%s)
mkdir -p "$STATE" "$LR/logs" "$LR/results/die_ci"
ts() { TZ=America/Los_Angeles date '+%F %H:%M'; }
log() { echo "$(ts) $*" | tee -a "$LR/logs/cron.log"; }
exec 9>"$STATE/lock"
if ! flock -n 9; then
  read -r OPID OSTART OMODE < "$STATE/run.pid" 2>/dev/null
  if [ "$MODE" = nightly ] && [ -n "${OPID:-}" ] && kill -0 "$OPID" 2>/dev/null; then
    log "nightly: a newer nightly starts; stopping the previous ${OMODE:-?} run (pid $OPID, started $(date -d @"${OSTART:-0}" '+%F %H:%M'))"
    kill -TERM "$OPID" 2>/dev/null
    flock -w 900 9 || { log "nightly: previous run (pid $OPID) still holds the lock after 15 min; NOT RUN"; exit 1; }
  else
    echo "die-ci: previous run still active"; exit 0
  fi
fi
echo "$$ $T0 $MODE" > "$STATE/run.pid"
: > "$STATE/otrun.pids"
rm -f "$STATE/stop.reason"
HOST=""; NAME=""; STAMP=""; SHA=""; PIDS=""
stop_run() {   # why
  [ -n "${STOPPED:-}" ] && return 0
  STOPPED=1
  log "$MODE ${SHA:-?}: STOPPED ($1); stopping its per-die jobs${HOST:+ on $HOST}"
  local p u units
  for p in $(cat "$STATE/otrun.pids" 2>/dev/null); do kill -TERM "$p" 2>/dev/null; done
  [ -n "$HOST" ] && [ -n "$NAME" ] || return 0
  units=$(grep -hoE 'oth-[A-Za-z0-9_.@-]+' "$LR"/logs/run_"${STAMP}"_*.log 2>/dev/null | sed 's/\.$//' | sort -u | tr '\n' ' ')
  ssh -o BatchMode=yes -o ConnectTimeout=20 "$HOST" "for u in $units; do systemctl --user stop \$u 2>/dev/null; done; \
    for c in \$(docker ps -q 2>/dev/null); do docker inspect -f '{{range .Mounts}}{{.Source}} {{end}}' \$c 2>/dev/null \
      | grep -qF '$R/results/die_ci/$NAME/' && docker stop -t 10 \$c >/dev/null; done" >/dev/null 2>&1
  log "$MODE ${SHA:-?}: NOT COMPLETED (stopped: $1; scopes: ${units:-none})"
}
on_term() {
  local why
  why=$(cat "$STATE/stop.reason" 2>/dev/null)
  stop_run "${why:-SIGTERM: a newer nightly or a systemd stop}"
  exit 143
}
trap on_term TERM INT
# watcher: wall-time cap + 2-h no-write watchdog on the run dir (only once a per-die job has started)
watch_run() {
  local now newest
  while sleep "$POLL_S"; do
    kill -0 $$ 2>/dev/null || return 0
    now=$(date +%s)
    if [ $(( now - T0 )) -gt "$MAX_S" ]; then
      echo "max runtime $(( MAX_S / 3600 )) h ($MAX_S s) reached" > "$STATE/stop.reason"; kill -TERM $$; return 0
    fi
    [ -n "$HOST" ] && [ -n "$NAME" ] && [ $(( now - T0 )) -gt "$IDLE_S" ] || continue
    grep -qsE 'oth-[A-Za-z0-9]' "$LR"/logs/run_"${STAMP}"_*.log || continue        # no per-die job started yet
    # progress = any write to the per-die client logs here (job start, output) or under the run dir on the host
    [ -n "$(find "$LR/logs" -maxdepth 1 -name "run_${STAMP}_*" -newermt @$(( now - IDLE_S )) -print -quit)" ] && continue
    newest=$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$HOST" \
      "if test -d $R/results/die_ci/$NAME; then find $R/results/die_ci/$NAME -newermt @$(( now - IDLE_S )) -print -quit; fi; echo PROBE_OK" 2>/dev/null)
    case "$newest" in
      PROBE_OK) echo "watchdog: no file under $R/results/die_ci/$NAME written for $(( IDLE_S / 60 )) min ($IDLE_S s)" > "$STATE/stop.reason"
                kill -TERM $$; return 0;;
    esac
  done
}

SHA=$(git -C "$HUB" rev-parse main) || exit 1
LAST=$(cat "$STATE/last_sha" 2>/dev/null || true)
if [ "$MODE" = commit ]; then
  [ "$SHA" = "$LAST" ] && exit 0
  if [ -n "$LAST" ] && git -C "$HUB" cat-file -e "$LAST" 2>/dev/null && \
     git -C "$HUB" diff --quiet "$LAST" "$SHA" -- tools/die_plan physical/die_plan; then
    echo "$SHA" > "$STATE/last_sha"; log "commit $SHA: no tools/die_plan or physical/die_plan change since ${LAST:0:10}; skipped"
    exit 0
  fi
  G2=auto
else
  G2=all
fi
MEM=$(python3 "$TOOLS/die_ci.py" job-mem hbm)          # the largest per-die job: hosts must admit it

# hosts that have the run root and a repo clone (intel2's ~/OpenTallas is a symlink into scratch2; every run fetches
# hub main first, so a lagging clone is fine)
CANDS=""
RUNHOSTS="intel1 intel2 epyc2"                         # EPYC1-RETIRE 2026-10-26: the hub itself is "localhost" in ot-run
[ "${OT_HUB_NAME:-epyc1}" = epyc1 ] || RUNHOSTS=$(echo " $RUNHOSTS " | sed "s/ ${OT_HUB_NAME} / localhost /")
for h in $RUNHOSTS; do
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$h" "mkdir -p $R && git -C ~/OpenTallas rev-parse --git-dir >/dev/null 2>&1" \
    && CANDS="$CANDS,$h"
done
CANDS=${CANDS#,}
[ -n "$CANDS" ] || { log "$MODE $SHA: NOT RUN (no scratch2 host with a repo clone)"; exit 1; }
HOST=$(ot-run --pick --mem "$MEM" --threads 16 --disk 150 --dir "$R" --hosts "$CANDS" 2>&1 | grep -oE '^(intel1|intel2|epyc2|localhost)\b' | head -1)
[ -n "$HOST" ] || HOST=${CANDS%%,*}
log "$MODE $SHA: run on $HOST (mem $MEM G, g2 $G2)"

# CI worktree at SHA on the run host (servers fetch main from the hub)
ssh "$HOST" "set -e; cd ~/OpenTallas && git fetch -q origin main && \
  if [ -d $R/wt/.git ] || [ -f $R/wt/.git ]; then git -C $R/wt checkout -q --detach $SHA; \
  else git worktree add -q --detach $R/wt $SHA; fi; git -C $R/wt rev-parse HEAD" > "$LR/logs/wt.log" 2>&1 \
  || { log "$MODE $SHA: NOT RUN (worktree on $HOST failed: $(tail -1 $LR/logs/wt.log))"; exit 1; }
# fail closed: the CI worktree must sit at the sha under test (a host clone can lag the hub: fetch above)
[ "$(tail -1 "$LR/logs/wt.log")" = "$SHA" ] || { log "$MODE $SHA: NOT RUN (worktree on $HOST at $(tail -1 $LR/logs/wt.log), not $SHA)"; exit 1; }
python3 "$TOOLS/die_ci.py" stage-views --views "$TOOLS/die_ci_views.json" \
  --host "$HOST" --dest "$R/views" > "$LR/logs/stage.log" 2>&1 || log "stage-views: some views not staged (see logs/stage.log)"
# previous run of record (localhost store): deltas + G2 carry
PREV=$(ls -1t "$LR"/results/die_ci/*/die_ci.json 2>/dev/null | head -1)
PREVARG="--prev none"
if [ -n "$PREV" ]; then
  ssh "$HOST" "mkdir -p $R/prev" && scp -q "$PREV" "$HOST:$R/prev/die_ci.json" && PREVARG="--prev $R/prev/die_ci.json"
fi
# die STA tool: main's tools/die_plan/die_sta.py, else DIE-STA's branch tip (provenance recorded in die_ci.json)
STAARG=""
if ! git -C "$HUB" cat-file -e "$SHA:tools/die_plan/die_sta.py" 2>/dev/null; then
  if STASHA=$(git -C "$HUB" rev-parse --verify -q "$STA_REF"); then
    mkdir -p "$LR/sta_tool" && git -C "$HUB" show "$STASHA:tools/die_plan/die_sta.py" > "$LR/sta_tool/die_sta.py" && \
    ssh "$HOST" "mkdir -p $R/sta_tool" && scp -q "$LR/sta_tool/die_sta.py" "$HOST:$R/sta_tool/die_sta.py" && \
    STAARG="--sta-tool $R/sta_tool/die_sta.py --sta-tool-ref $STA_REF@${STASHA:0:10}"
  fi
fi
NAME="$(date +%F)_${SHA:0:12}"
STAMP="$(date +%Y%m%d_%H%M)_${SHA:0:10}"
watch_run 9>&- &
WATCH=$!
DIES=$(ssh "$HOST" "cd $R/wt && python3 -c \"import sys; sys.path.insert(0,'tools/die_plan'); import die_ci; print(' '.join(die_ci.resolve_plans('.')))\"")
log "$MODE $SHA: per-die jobs on $HOST: $DIES"
ssh "$HOST" "rm -rf $R/results/die_ci/$NAME"
PIDS=""
for d in $DIES; do
  M=$(ssh "$HOST" "cd $R/wt && python3 tools/die_plan/die_ci.py job-mem $d")
  # Harvest each completed die immediately. A congested probe on another die can
  # take hours; it must not hide the completed gates until the whole batch ends.
  {
  trap - TERM INT
  ot-run --hosts "$HOST" --mem "$M" --threads 8 --dir "$R" --priority die -- \
    bash -lc "export PATH=\$HOME/.local/opentallas-tools/bin:\$PATH; cd $R/wt && python3 tools/die_plan/die_ci.py run \
      --sha $SHA --mode $MODE --g2 $G2 --out $R/results/die_ci --name $NAME --partial --dies $d \
      --views-root $R/views $PREVARG $STAARG --jobs 1" > "$LR/logs/run_${STAMP}_$d.log" 2>&1 9>&- &
  OP=$!
  echo "$OP" >> "$STATE/otrun.pids"
  wait "$OP"
  RC=$?
  PARTIAL="$LR/partials/die_ci/$NAME"
  mkdir -p "$PARTIAL"
  if rsync -a --include="/$d.json" --include="/$d.md" --include="/part_$d.json" --exclude='*' \
      "$HOST:$R/results/die_ci/$NAME/" "$PARTIAL/" >> "$LR/logs/run_${STAMP}_$d.log" 2>&1; then
    if [ -s "$PARTIAL/part_$d.json" ]; then
      log "$MODE $SHA: die $d finished (exit $RC); record $PARTIAL/$d.md; other dies may still be running"
    else
      log "$MODE $SHA: die $d exited $RC without a completed record (see logs/run_${STAMP}_$d.log)"
    fi
  else
    log "$MODE $SHA: die $d exited $RC; partial harvest FAILED (see logs/run_${STAMP}_$d.log)"
  fi
  exit "$RC"
  } &
  PIDS="$PIDS $!"
done
for p in $PIDS; do wait $p; done
kill "$WATCH" 2>/dev/null
RDIR=$R/results/die_ci/$NAME
ssh "$HOST" "cd $R/wt && python3 tools/die_plan/die_ci.py collect $RDIR --expect ${DIES// /,}" > "$LR/logs/run_${STAMP}_collect.log" 2>&1
RUN=$(grep -oE "DIE-CI (PASS|FAIL|INCOMPLETE): \S+/SUMMARY.md" "$LR/logs/run_${STAMP}_collect.log" | tail -1)
[ -n "$RUN" ] || { log "$MODE $SHA: NOT COMPLETED (collect failed; $LR/logs/run_${STAMP}_*.log)"; exit 1; }
VERDICT=$(echo "$RUN" | awk '{print $2}' | tr -d :)
rsync -a "$HOST:$RDIR/" "$LR/results/die_ci/$NAME/" || { log "rsync back failed"; exit 1; }
# keep only this run on the run host (scratch2 space; the localhost copy is the store)
ssh "$HOST" "cd $R/results/die_ci && ls -1 | grep -vx '$NAME' | xargs -r rm -rf"
echo "$SHA" > "$STATE/last_sha"

# commit the run record (JSON + MD, no raw work/) to the results branch
if [ ! -e "$RESW/.git" ]; then
  git -C "$HUB" worktree add -q "$RESW" "$RESB" 2>/dev/null || git -C "$HUB" worktree add -q -b "$RESB" "$RESW" "$SHA"
fi
D="$RESW/results/die_ci/$NAME"; mkdir -p "$D"
( cd "$LR/results/die_ci/$NAME" && cp -f die_ci.json SUMMARY.md *.md *.json "$D/" 2>/dev/null; \
  mkdir -p "$D/xdie" && cp -f work/xdie*/*.json "$D/xdie/" 2>/dev/null; true )
git -C "$RESW" add "results/die_ci/$NAME"
git -C "$RESW" commit -q -m "DIE-CI $MODE main ${SHA:0:10}: $VERDICT ($NAME)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git -C "$RESW" push -q origin "$RESB" || true

# HANDOFF: one live "DIE-CI LATEST:" line (replaced in place) + a milestone line when the verdict changes
SUM="$LR/results/die_ci/$NAME/SUMMARY.md"
OLDV=$(cat "$STATE/last_verdict" 2>/dev/null || true)
python3 - "$HANDOFF" "$(ts) PDT DIE-CI LATEST: $SUM ($VERDICT, main ${SHA:0:10}, $MODE; branch $RESB)" <<'EOF'
import os, sys
p, line = sys.argv[1], sys.argv[2]
txt = open(p).read().splitlines() if os.path.exists(p) else []
txt = [l for l in txt if "DIE-CI LATEST:" not in l] + [line]
tmp = p + ".die-ci.tmp"
open(tmp, "w").write("\n".join(txt) + "\n")
os.replace(tmp, p)
EOF
if [ "$VERDICT" != "$OLDV" ]; then
  echo "$(ts) PDT DIE-CI: verdict ${OLDV:-none} -> $VERDICT on main ${SHA:0:10} ($MODE): $SUM" >> "$HANDOFF"
fi
echo "$VERDICT" > "$STATE/last_verdict"
log "$MODE $SHA: $VERDICT -> $SUM"
