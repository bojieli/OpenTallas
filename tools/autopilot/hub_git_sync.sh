#!/bin/bash
# hub_git_sync.sh -- keep the epyc1 hub checkouts current (installed as ~/bin/hub-git-sync.sh; ExecStartPre of
# autopilot.service and of the die-ci / release-task-watch units).
#
#   hub_git_sync.sh coord   sync the coordination checkout ~/coord (branch coord/state) MERGE-BASED, like
#                           bin/coord-commit.sh:
#                           (1) dirty APPEND-ONLY logs (HANDOFF.md, CODEX-LOG.md, CODEX-HANDOFF.md, lanes/*.md,
#                               autopilot/queue.tsv, autopilot/resolved.tsv) are committed as they are (agents and
#                               die_ci_cron.sh append lines in this checkout); any OTHER tracked edit -> FAIL, untouched;
#                           (1b) GENERATED files (RELEASE_TREE.md, rewritten on the hub by release_tree_plan.py; the
#                               coordinator commits it from its own checkout) never stall a sync: a local edit is
#                               discarded and origin's copy wins a merge conflict (KW-FIX-25 11-06: 12 hub commits
#                               and every intel2 post sat unpushed 22:22-23:0x on this one file);
#                           (1c) LIVE-STATE files (autopilot/kit_wave_state.json, rewritten every tick by the autopilot and
#                               by KW-FIX row edits on the hub; tracked in git) never stall a sync (KW-FIX-46 11-11: HUB-SYNC-FAILED
#                               2026-11-09 19:08 -> 11-11 07:18, ~36 h of stale kit_wave.json): a dirty copy is tolerated, never
#                               committed, never discarded; when the merge would change it, the local bytes are saved, the path
#                               reset for the merge and the saved bytes restored afterwards (the live file keeps its content);
#                           (2) fetch + merge origin coord/state (never rebase, never stash, never reset);
#                               conflicts in append-only logs are resolved by UNION (both sides' lines kept;
#                               a doubled "DIE-CI LATEST:" line keeps the newest); any other conflict -> merge --abort, FAIL;
#                           (3) push local commits to coord/state (retry: fetch + merge again).
#                           FAIL is LOUD: autopilot/HUB-SYNC-FAILED ("since <first failure>" + reason) is written and
#                           the autopilot puts "HUB-SYNC-FAILED since <time>: <reason>" on the first line of
#                           LOOP-GAPS.txt until a sync succeeds (10-25: the hub sat at 08:29 for 86 min because a local
#                           commit + uncommitted CODEX-LOG/HANDOFF lines made the fast-forward-only pull fail silently).
#                           Success writes autopilot/HUB-SYNC-OK and removes HUB-SYNC-FAILED.
#   hub_git_sync.sh repo    fast-forward ~/OpenTallas main to origin/main (clean tree only; never pushes).
#
# env (tests): HUB_SYNC_COORD (coordination checkout), HUB_SYNC_REPO, HUB_SYNC_BRANCH (default coord/state).
set -uo pipefail
C=${HUB_SYNC_COORD:-$HOME/coord}; R=${HUB_SYNC_REPO:-$HOME/OpenTallas}; B=${HUB_SYNC_BRANCH:-coord/state}
URL=git@github.com:bojieli/OpenTallas.git
APPEND_RE='^(HANDOFF\.md|CODEX-LOG\.md|CODEX-HANDOFF\.md|lanes/[^/]+\.md|lanes/SIGN-RATE\.tsv|autopilot/(queue|resolved)\.tsv)$'
GENERATED_RE='^RELEASE_TREE\.md$'
LIVE_RE='^autopilot/kit_wave_state\.json$'
FLEET_AFTER_MIN=${HUB_SYNC_FLEET_AFTER_MIN:-30}
say() { echo "hub-git-sync $1: $2"; }
now() { date '+%Y-%m-%d %H:%M %Z'; }

if [ "${1:-}" = repo ]; then
  [ "$(git -C "$R" rev-parse --abbrev-ref HEAD)" = main ] || { say repo "$R not on main"; exit 1; }
  [ -z "$(git -C "$R" status --porcelain --untracked-files=no)" ] || { say repo "$R has local edits; not updated"; exit 1; }
  git -C "$R" fetch -q origin main && git -C "$R" merge -q --ff-only origin/main || { say repo "fetch/ff failed"; exit 1; }
  say repo "main at $(git -C "$R" rev-parse --short=10 HEAD)"; exit 0
fi
[ "${1:-}" = coord ] || { echo "usage: $0 coord|repo" >&2; exit 2; }

cd "$C" || { say coord "no checkout $C"; exit 1; }
AP="$C/autopilot"; mkdir -p "$AP"
fail() {   # loud: keep the FIRST failure time across consecutive failures
  local since
  since=$(sed -n 's/^since //p' "$AP/HUB-SYNC-FAILED" 2>/dev/null | head -1)
  [ -n "$since" ] || since=$(now)
  printf 'since %s\n%s (last attempt %s, %s)\n' "$since" "$1" "$(now)" "$(git rev-parse --short=10 HEAD 2>/dev/null)" \
    > "$AP/.HUB-SYNC-FAILED.$$" && mv -f "$AP/.HUB-SYNC-FAILED.$$" "$AP/HUB-SYNC-FAILED"
  say coord "FAILED since $since: $1" >&2
  alert "HUB-SYNC-FAILED since $since: $1"
  live_restore
  fleet_alert "$1"
  exit 1
}
alert() {   # KW-FIX-35 11-08: one ALERT line in the autopilot log (fail_watch / LOOP-GAP grep it); 2.5 h went unseen
  local ab
  ab=$(git rev-list --left-right --count "HEAD...origin/$B" 2>/dev/null | awk '{print "ahead "$1", behind "$2}')
  printf '%s AUTOPILOT: ALERT %s (%s checkout %s; %s)\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$1" "$(hostname)" "$C" \
    "${ab:-ahead/behind unknown}" >> "${HUB_SYNC_LOG:-$AP/log.txt}" 2>/dev/null || true
}
ok() {
  live_restore
  rm -f "$AP/HUB-SYNC-FAILED" "$AP/.HUB-SYNC-FLEET-POSTED"
  printf '%s %s\n' "$(now)" "$(git rev-parse --short=10 HEAD)" > "$AP/.HUB-SYNC-OK.$$" && mv -f "$AP/.HUB-SYNC-OK.$$" "$AP/HUB-SYNC-OK"
  say coord "$1"; exit 0
}
is_append() { printf '%s\n' "$1" | grep -Eq "$APPEND_RE"; }
is_generated() { printf '%s\n' "$1" | grep -Eq "$GENERATED_RE"; }
is_live() { printf '%s\n' "$1" | grep -Eq "$LIVE_RE"; }
LIVE_SAVED=""
live_restore() {   # put the saved live-state bytes back (EXIT trap too: a failed merge must not lose them)
  local f
  for f in $LIVE_SAVED; do
    [ -f "$AP/.hub-sync-live/$f" ] && cp -f -- "$AP/.hub-sync-live/$f" "$f.hubsync.tmp" && mv -f -- "$f.hubsync.tmp" "$f" && rm -f -- "$AP/.hub-sync-live/$f"
  done
  LIVE_SAVED=""
}
trap live_restore EXIT
live_stash() {   # $1 = merge target; for each dirty live file that the merge would change: save bytes, reset the path
  local f
  for f in $LIVE_DIRTY; do
    [ -n "$(git diff --name-only HEAD "$1" -- "$f")" ] || continue
    mkdir -p "$AP/.hub-sync-live/$(dirname "$f")" && cp -f -- "$f" "$AP/.hub-sync-live/$f" || fail "cannot save live state $f"
    LIVE_SAVED="$LIVE_SAVED $f"; git checkout -q -- "$f"
    say coord "live state $f kept aside for the merge"
  done
}
fleet_alert() {   # HUB-SYNC-FAILED older than FLEET_AFTER_MIN: ONE FLEET line in the queue per 6 h (best effort, never blocks)
  local since ts age mk="$AP/.HUB-SYNC-FLEET-POSTED"
  since=$(sed -n 's/^since //p' "$AP/HUB-SYNC-FAILED" 2>/dev/null | head -1)
  ts=$(date -d "$(printf '%s' "$since" | sed 's/ [A-Z]*$//')" +%s 2>/dev/null) || return 0
  age=$(( ($(date +%s) - ts) / 60 )); [ "$age" -ge "$FLEET_AFTER_MIN" ] || return 0
  [ -z "$(find "$mk" -mmin -360 2>/dev/null)" ] || return 0
  [ -f lanes/COORD-REVIEW-QUEUE.md ] || return 0
  printf -- '- %s FLEET [hub-git-sync %s] HUB-SYNC-FAILED for %s min (since %s): %s. The autopilot reads a stale coord checkout until it clears.\n' \
    "$(date '+%Y-%m-%d %H:%M %Z')" "$(hostname)" "$age" "$since" "$1" >> lanes/COORD-REVIEW-QUEUE.md
  : > "$mk"
  git commit -q -m "hub $(hostname): FLEET line, HUB-SYNC-FAILED ${age} min" -- lanes/COORD-REVIEW-QUEUE.md >/dev/null 2>&1 \
    && timeout 60 git push -q origin "HEAD:$B" >/dev/null 2>&1 || true
}
dedupe_latest() {   # HANDOFF.md: ONE "DIE-CI LATEST:" line (die_ci_cron.sh replaces it in place); $1 = the line to keep
  [ -f HANDOFF.md ] || return 0
  [ "$(grep -c 'DIE-CI LATEST:' HANDOFF.md)" -gt 1 ] || return 0
  python3 -I - HANDOFF.md "${1:-}" <<'EOF'
import sys
p, want = sys.argv[1], sys.argv[2]
lines = open(p).read().splitlines()
idx = [i for i, l in enumerate(lines) if "DIE-CI LATEST:" in l]
keep = lines[idx[-1]] if want not in [lines[i] for i in idx] else want
out, done = [], False
for i, l in enumerate(lines):
    if i in idx:
        if not done:
            out.append(keep)
            done = True
        continue
    out.append(l)
open(p, "w").write("\n".join(out) + "\n")
EOF
}
latest_of() { grep -m1 'DIE-CI LATEST:' "$1" 2>/dev/null || true; }
merge_union() {   # merge $1; union-resolve append-only conflicts; 0 = merged, 1 = refused (aborted)
  git merge -q --no-edit -m "Merge origin/$B into hub $(hostname) checkout (hub-git-sync)" "$1" >/dev/null 2>&1 && return 0
  local f bad="" t
  if [ ! -f "$(git rev-parse --git-dir)/MERGE_HEAD" ]; then
    # KW-FIX-35 11-08: Codex wrote 3 handoff/*.md untracked here and committed them elsewhere; every merge was refused
    # 04:32-06:58 (34 ahead / 256 behind).  Untracked copies byte-identical to the incoming file are moved aside (kept
    # under autopilot/.hub-sync-untracked/) and the merge is retried once; a differing copy still refuses, by name.
    local mb f moved="" differ=""
    mb=$(git merge-base HEAD "$1")
    for f in $(git diff --name-only --diff-filter=A "$mb" "$1"); do
      [ -e "$f" ] && ! git ls-files --error-unmatch -- "$f" >/dev/null 2>&1 || continue
      if git show "$1:$f" | cmp -s - "$f"; then
        mkdir -p "$AP/.hub-sync-untracked/$(dirname "$f")" && mv -f -- "$f" "$AP/.hub-sync-untracked/$f" && moved="$moved $f"
      else differ="$differ $f"; fi
    done
    [ -z "$differ" ] || { MERGE_ERR="merge refused: untracked local file(s) differ from origin:$differ"; return 1; }
    [ -n "$moved" ] && say coord "moved identical untracked files aside:$moved" \
      && git merge -q --no-edit -m "Merge origin/$B into hub $(hostname) checkout (hub-git-sync)" "$1" >/dev/null 2>&1 && return 0
    [ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] || { MERGE_ERR="merge refused (local untracked file in the way?)"; return 1; }
  fi
  for f in $(git diff --name-only --diff-filter=U); do
    if is_generated "$f"; then
      git checkout -q --theirs -- "$f" && git add -- "$f" || bad="$bad $f"
    elif is_append "$f"; then
      t=$(mktemp -d)
      git show ":1:$f" > "$t/base" 2>/dev/null || : > "$t/base"
      git show ":2:$f" > "$t/ours" 2>/dev/null || : > "$t/ours"
      git show ":3:$f" > "$t/theirs" 2>/dev/null || : > "$t/theirs"
      if [ "$f" = HANDOFF.md ]; then   # keep the side that CHANGED the DIE-CI LATEST line (ours first)
        LB=$(latest_of "$t/base"); LO=$(latest_of "$t/ours"); LT=$(latest_of "$t/theirs")
        if [ "$LO" != "$LB" ]; then KEEP=$LO; elif [ "$LT" != "$LB" ]; then KEEP=$LT; else KEEP=$LO; fi
      fi
      git merge-file --union "$t/ours" "$t/base" "$t/theirs"
      cp "$t/ours" "$f"; rm -rf "$t"
      [ "$f" = HANDOFF.md ] && dedupe_latest "$KEEP"
      git add -- "$f"
    else
      bad="$bad $f"
    fi
  done
  if [ -n "$bad" ]; then git merge --abort; MERGE_ERR="conflict outside the append-only logs:$bad (merge aborted, nothing discarded)"; return 1; fi
  git commit -q --no-edit >/dev/null || { git merge --abort; MERGE_ERR="union merge commit failed"; return 1; }
}

exec 9>"$C/.coord.lock"; flock -w 300 9 || fail "coord lock busy > 300 s"
git remote get-url origin >/dev/null 2>&1 || git remote add origin "$URL"
[ "$(git rev-parse --abbrev-ref HEAD)" = "$B" ] || fail "checkout not on $B"
[ ! -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] || fail "an unfinished merge sits in the checkout"
[ -z "$(git diff --name-only --diff-filter=U)" ] || fail "unmerged paths in the checkout"

# (1) commit dirty append-only logs; refuse anything else
DIRTY=$(git status --porcelain --untracked-files=no | sed 's/^...//; s/.* -> //')
OTHER=""; APP=""; LIVE_DIRTY=""
for f in $DIRTY; do
  if is_generated "$f"; then git checkout -q -- "$f" && say coord "discarded local edit of generated $f"
  elif is_live "$f"; then LIVE_DIRTY="$LIVE_DIRTY $f"
  elif is_append "$f"; then APP="$APP $f"; else OTHER="$OTHER $f"; fi
done
[ -z "$OTHER" ] || fail "non-log local edits in the hub checkout, not touched:$OTHER"
if [ -n "$APP" ]; then
  case " $APP " in *" HANDOFF.md "*) dedupe_latest;; esac
  # shellcheck disable=SC2086
  git commit -q -m "hub $(hostname): commit uncommitted append-only log lines ($(echo $APP))

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- $APP || fail "commit of dirty logs failed:$APP"
fi

# (2)+(3) merge origin, push local commits
MERGE_ERR=""
for i in 1 2 3 4 5; do
  git fetch -q origin "$B" || { MERGE_ERR="fetch failed"; sleep 5; continue; }
  if ! git merge-base --is-ancestor FETCH_HEAD HEAD; then
    KEEP=$(latest_of HANDOFF.md)
    live_stash FETCH_HEAD
    merge_union FETCH_HEAD || fail "$MERGE_ERR"
    live_restore
    dedupe_latest "$KEEP"
    if [ -n "$(git status --porcelain --untracked-files=no -- HANDOFF.md)" ]; then
      git commit -q -m "hub $(hostname): one DIE-CI LATEST line after merge" -- HANDOFF.md || fail "dedupe commit failed"
    fi
  fi
  BEHIND=$(git rev-list --count HEAD..FETCH_HEAD)
  [ "$BEHIND" -le "${HUB_SYNC_MAX_BEHIND:-5}" ] || alert "hub checkout $BEHIND commits behind origin $B after merge"
  [ -n "$(git rev-list FETCH_HEAD..HEAD)" ] || ok "checkout at $(git rev-parse --short=10 HEAD) (= origin $B)"
  if git push -q origin "HEAD:$B" 2>/dev/null; then ok "pushed hub commits: $(git rev-parse --short=10 HEAD)"; fi
  MERGE_ERR="push to $B rejected"; sleep 3
done
fail "${MERGE_ERR:-sync failed} after 5 attempts"
