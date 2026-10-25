#!/bin/bash
# hub_git_sync.sh -- keep the epyc1 hub checkouts current (installed as ~/bin/hub-git-sync.sh; ExecStartPre of
# autopilot.service and of the die-ci / release-task-watch units).
#
#   hub_git_sync.sh coord   sync the coordination checkout ~/coord (branch coord/state) MERGE-BASED, like
#                           bin/coord-commit.sh:
#                           (1) dirty APPEND-ONLY logs (HANDOFF.md, CODEX-LOG.md, CODEX-HANDOFF.md, lanes/*.md,
#                               autopilot/queue.tsv, autopilot/resolved.tsv) are committed as they are (agents and
#                               die_ci_cron.sh append lines in this checkout); any OTHER tracked edit -> FAIL, untouched;
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
APPEND_RE='^(HANDOFF\.md|CODEX-LOG\.md|CODEX-HANDOFF\.md|lanes/[^/]+\.md|autopilot/(queue|resolved)\.tsv)$'
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
  exit 1
}
ok() {
  rm -f "$AP/HUB-SYNC-FAILED"
  printf '%s %s\n' "$(now)" "$(git rev-parse --short=10 HEAD)" > "$AP/.HUB-SYNC-OK.$$" && mv -f "$AP/.HUB-SYNC-OK.$$" "$AP/HUB-SYNC-OK"
  say coord "$1"; exit 0
}
is_append() { printf '%s\n' "$1" | grep -Eq "$APPEND_RE"; }
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
  [ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] || { MERGE_ERR="merge refused (local untracked file in the way?)"; return 1; }
  for f in $(git diff --name-only --diff-filter=U); do
    if is_append "$f"; then
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
OTHER=""; APP=""
for f in $DIRTY; do if is_append "$f"; then APP="$APP $f"; else OTHER="$OTHER $f"; fi; done
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
    merge_union FETCH_HEAD || fail "$MERGE_ERR"
    dedupe_latest "$KEEP"
    if [ -n "$(git status --porcelain --untracked-files=no -- HANDOFF.md)" ]; then
      git commit -q -m "hub $(hostname): one DIE-CI LATEST line after merge" -- HANDOFF.md || fail "dedupe commit failed"
    fi
  fi
  [ -n "$(git rev-list FETCH_HEAD..HEAD)" ] || ok "checkout at $(git rev-parse --short=10 HEAD) (= origin $B)"
  if git push -q origin "HEAD:$B" 2>/dev/null; then ok "pushed hub commits: $(git rev-parse --short=10 HEAD)"; fi
  MERGE_ERR="push to $B rejected"; sleep 3
done
fail "${MERGE_ERR:-sync failed} after 5 attempts"
