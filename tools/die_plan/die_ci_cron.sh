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
LR=/srv/opentallas-scratch/claude/die-ci             # localhost results + logs
R=/srv/opentallas-scratch2/claude/die-ci             # run root on the scratch2 hosts (owner: never root disks)
RESW=$HOME/wt/die-ci-results                         # results branch worktree (localhost)
RESB=claude/die-ci-results
HANDOFF=$HOME/coord/HANDOFF.md
MEM_COMMIT=${DIE_CI_MEM_COMMIT:-48}                  # 5 dies x (G0C + ILM STA) + G2 for changed dies (die probe 64 G
MEM_NIGHTLY=${DIE_CI_MEM_NIGHTLY:-340}               #   peak, 5 in parallel) -> nightly reserves the full G2 set
mkdir -p "$STATE" "$LR/logs" "$LR/results/die_ci"
exec 9>"$STATE/lock"
flock -n 9 || { echo "die-ci: previous run still active"; exit 0; }
ts() { TZ=America/Los_Angeles date '+%F %H:%M'; }
log() { echo "$(ts) $*" | tee -a "$LR/logs/cron.log"; }

SHA=$(git -C "$HUB" rev-parse main) || exit 1
LAST=$(cat "$STATE/last_sha" 2>/dev/null || true)
if [ "$MODE" = commit ]; then
  [ "$SHA" = "$LAST" ] && exit 0
  if [ -n "$LAST" ] && git -C "$HUB" cat-file -e "$LAST" 2>/dev/null && \
     git -C "$HUB" diff --quiet "$LAST" "$SHA" -- tools/die_plan physical/die_plan; then
    echo "$SHA" > "$STATE/last_sha"; log "commit $SHA: no tools/die_plan or physical/die_plan change since ${LAST:0:10}; skipped"
    exit 0
  fi
  MEM=$MEM_COMMIT; G2=auto
else
  MEM=$MEM_NIGHTLY; G2=all
fi

# hosts that have the run root and a repo clone (FLEET: intel2's ~/OpenTallas was moved off on 10-24)
CANDS=""
for h in intel1 intel2 epyc2; do
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$h" "mkdir -p $R && git -C ~/OpenTallas rev-parse --git-dir >/dev/null 2>&1" \
    && CANDS="$CANDS,$h"
done
CANDS=${CANDS#,}
[ -n "$CANDS" ] || { log "$MODE $SHA: NOT RUN (no scratch2 host with a repo clone)"; exit 1; }
HOST=$(ot-run --pick --mem "$MEM" --threads 16 --dir "$R" --hosts "$CANDS" 2>&1 | grep -oE '^(intel1|intel2|epyc2)\b' | head -1)
[ -n "$HOST" ] || HOST=${CANDS%%,*}
log "$MODE $SHA: run on $HOST (mem $MEM G, g2 $G2)"

# CI worktree at SHA on the run host (servers fetch main from the hub)
ssh "$HOST" "set -e; cd ~/OpenTallas && git fetch -q origin main && \
  if [ -d $R/wt/.git ] || [ -f $R/wt/.git ]; then git -C $R/wt checkout -q --detach $SHA; \
  else git worktree add -q --detach $R/wt $SHA; fi; git -C $R/wt rev-parse HEAD" > "$LR/logs/wt.log" 2>&1 \
  || { log "$MODE $SHA: NOT RUN (worktree on $HOST failed: $(tail -1 $LR/logs/wt.log))"; exit 1; }
python3 "$TOOLS/die_ci.py" stage-views --views "$TOOLS/die_ci_views.json" \
  --host "$HOST" --dest "$R/views" > "$LR/logs/stage.log" 2>&1 || log "stage-views: some views not staged (see logs/stage.log)"
# previous run of record (localhost store): deltas + G2 carry
PREV=$(ls -1d "$LR"/results/die_ci/*/die_ci.json 2>/dev/null | sort | tail -1)
PREVARG="--prev none"
if [ -n "$PREV" ]; then
  ssh "$HOST" "mkdir -p $R/prev" && scp -q "$PREV" "$HOST:$R/prev/die_ci.json" && PREVARG="--prev $R/prev/die_ci.json"
fi
RUNLOG="$LR/logs/run_$(date +%Y%m%d_%H%M)_${SHA:0:10}.log"
ot-run --hosts "$HOST" --mem "$MEM" --threads 16 --dir "$R" --priority die -- \
  bash -lc "export PATH=\$HOME/.local/opentallas-tools/bin:\$PATH; cd $R/wt && python3 tools/die_plan/die_ci.py run \
    --sha $SHA --mode $MODE --g2 $G2 --out $R/results/die_ci --views-root $R/views $PREVARG --jobs 6" > "$RUNLOG" 2>&1
RC=$?
RUN=$(grep -oE "DIE-CI (PASS|FAIL|INCOMPLETE): \S+/SUMMARY.md" "$RUNLOG" | tail -1)
[ -n "$RUN" ] || { log "$MODE $SHA: NOT COMPLETED (ot-run rc $RC; $RUNLOG)"; exit 1; }
VERDICT=$(echo "$RUN" | awk '{print $2}' | tr -d :)
RDIR=$(dirname "$(echo "$RUN" | awk '{print $3}')")
NAME=$(basename "$RDIR")
rsync -a "$HOST:$RDIR/" "$LR/results/die_ci/$NAME/" || { log "rsync back failed"; exit 1; }
echo "$SHA" > "$STATE/last_sha"

# commit the run record (JSON + MD, no raw work/) to the results branch
if [ ! -e "$RESW/.git" ]; then
  git -C "$HUB" worktree add -q "$RESW" "$RESB" 2>/dev/null || git -C "$HUB" worktree add -q -b "$RESB" "$RESW" "$SHA"
fi
D="$RESW/results/die_ci/$NAME"; mkdir -p "$D"
( cd "$LR/results/die_ci/$NAME" && cp -f die_ci.json SUMMARY.md *.md *.json "$D/" 2>/dev/null; \
  mkdir -p "$D/xdie" && cp -f work/xdie/*.json "$D/xdie/" 2>/dev/null; true )
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
