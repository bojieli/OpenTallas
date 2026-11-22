#!/bin/bash
# usage: coord-commit.sh "message" file1 [file2 ...]   (paths relative to ~/coord) -- serialised commit+push of coord/state
# COORD-COMMIT-SPEED-1 11-13: two locks, group commit. Measured 11-13: a push of coord/state waits 15-75 s (up to 290 s) on
# GitHub receive-pack (client side ~2.5 s), so one push per post made 14 posts queue ~10 min. Now:
#   .coord.lock      (fd 9) guards the shared worktree/index: add+commit, preserve, fetch+merge, restore. Held seconds.
#   .coord.push.lock (fd 8) one pusher at a time. Pushes a fixed sha with fd 9 released, so later posters commit meanwhile.
# A waiter that gets fd 8 fetches first: if its own commit (or, with nothing of its own, HEAD) is already on origin --
# an earlier holder pushed it, or committed its lines through preserve_append_logs -- it exits 0 without merge or push.
# Safety kept: KW-FIX-25 re-apply (restore_own), KW-FIX-17 merge abort, append preservation, generated-file discard,
# never rebase/stash/reset. Env (tests only): COORD_DIR, COORD_BRANCH. Timing log: ~/.local/state/coord-commit-times.log
# REPO-STATE-1 11-14: (1) a commit that names lanes/posts/<LANE>.md (bin/post.sh) also runs tools/queue_view.py under fd 9
# and commits the lanes/COORD-REVIEW-QUEUE.md view with it. (2) when the merge of origin conflicts (on a file this call
# did not touch, e.g. another clone's edit), the call no longer retries the same merge 6x and fails: replay_own builds
# one commit on origin's tip that carries ONLY this call's own file changes (unchanged upstream -> our version; pure
# append -> our appended lines on top of upstream; anything else -> no replay) in a private index, pushes it, and
# leaves the shared worktree and index untouched (the local HEAD merges it cleanly later: same change on both sides).
# FLOW-HEALTH-1 11-15 (COORD): the script always ends with one status line on stdout: "PUSHED <sha>" (origin/$B holds the commit) or
# "FAILED <reason>" (exit 1; also stderr).  3 attempts with backoff 3/12/27 s.  A dirty or untracked file outside the named paths never
# blocks a post: when the merge in the shared tree is refused, only this call's own changes are replayed onto origin in a private index.
set -eE
trap 'rc=$?; echo "FAILED unexpected command failure (exit $rc) at line $LINENO: $BASH_COMMAND" | tee /dev/stderr; exit 1' ERR
C=${COORD_DIR:-/home/ubuntu/coord}; B=${COORD_BRANCH:-coord/state}
cd "$C"
# COORD-GUARD 11-19 (incident: a `checkout -f -B` in this worktree replaced the coord files with main): never commit, merge or push from a worktree that
# is not on $B, and say so.  tools/fleet/coord-branch-guard puts a mistaken checkout back; this stops anything that slipped through.
cur=$(git symbolic-ref -q --short HEAD 2>/dev/null || true)
if [ "$cur" != "$B" ]; then
  echo "FAILED worktree $C is on '${cur:-detached HEAD}', not $B: nothing committed or pushed (run: git checkout $B here, after checking the files)" | tee /dev/stderr
  exit 1
fi
msg="$1"; shift
# FLOW-PROC-B 11-21: a commit that names lanes/LANE-STATUS.tsv must leave it schema-clean (tools/lane_status.py --check); only bin/stand-down.sh writes stood-down rows.
for _f in "$@"; do
  if [ "$_f" = "lanes/LANE-STATUS.tsv" ] && [ -f "$C/tools/lane_status.py" ]; then
    if ! _lsb=$(python3 -I "$C/tools/lane_status.py" --check "$C/lanes/LANE-STATUS.tsv" 2>&1); then
      echo "FAILED lanes/LANE-STATUS.tsv fails the schema (use bin/stand-down.sh LANE SUCCESSOR): $_lsb" | head -8 | tee /dev/stderr; exit 1
    fi
  fi
done
now() { date +%s.%N; }
T0=$(now)
TLOG=${COORD_COMMIT_TLOG:-$HOME/.local/state/coord-commit-times.log}
tlog() { printf '%s pid=%s mode=%s wait9=%.1f wait8=%.1f push=%.1f total=%.1f tries=%s msg=%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$$" "$1" \
  "$W9" "$W8" "$TP" "$(echo "$(now)-$T0" | bc)" "$i" "${msg:0:60}" >> "$TLOG" 2>/dev/null || true; }
W9=0; W8=0; TP=0; i=0
exec 9>"$C/.coord.lock"
exec 8>"$C/.coord.push.lock"
t=$(now); flock 9; W9=$(echo "$(now)-$t" | bc)
ORIG=("$@")
# FLOW-FLEET-R2 S1 11-22: refuse invalid UTF-8 in the lines this commit adds to a named text file (bin/utf8_guard.py; COORD_UTF8_GUARD=off skips)
_g="$C/bin/utf8_guard.py"
if [ -f "$_g" ] && ! _gm=$(python3 -I "$_g" --files "$C" "$@" 2>&1); then
  echo "FAILED $_gm" | head -6 | tee /dev/stderr; flock -u 9; exit 1
fi
git add -- "$@"
# NOTHING-COMMITTED (COORD 11-19, SONNET-FIX-QC): "no changes added to commit" followed by PUSHED hid a handoff that never committed.
# After staging, the named paths must differ from HEAD; if not, say so, exit 1 (nothing is pushed on their behalf).
if git diff --cached --quiet -- "$@"; then
  echo "NOTHING-COMMITTED: $*" | tee /dev/stderr; flock -u 9; exit 1
fi
for a in "$@"; do case "$a" in lanes/posts/*.md)
  if [ -f "$C/tools/queue_view.py" ] && [ "$*" != "lanes/COORD-REVIEW-QUEUE.md" ]; then
    COORD_DIR="$C" timeout 120 python3 -I "$C/tools/queue_view.py" --coord "$C" --apply >/dev/null 2>&1 || true
    git diff --quiet -- lanes/COORD-REVIEW-QUEUE.md || { set -- "$@" lanes/COORD-REVIEW-QUEUE.md; git add -- lanes/COORD-REVIEW-QUEUE.md; }
  fi; break;; esac; done
own_before=$(git rev-parse HEAD)
git commit -q -m "$msg" -- "$@" || true
# KW-FIX-25 11-06: a lane's own `git reset --keep origin/coord/state` in this shared tree does not take our lock. Between our
# commit and our push it silently dropped the commit (9 commits, 20 queue lines today). Remember what we committed, re-apply it
# if it left HEAD, and exit 0 only when origin holds it.
OWN=""; [ "$(git rev-parse HEAD)" = "$own_before" ] || OWN=$(git rev-parse HEAD)
flock -u 9
restore_own() {
[ -n "$OWN" ] || return 0
git merge-base --is-ancestor "$OWN" HEAD && return 0
git merge -q --no-edit "$OWN" 2>/dev/null && return 0
git merge --abort 2>/dev/null || true
OWN="$OWN" python3 -I - "$@" <<'PY_OWN'
import os, subprocess as S, sys
own = os.environ["OWN"]
g = lambda *a: S.run(["git", *a], capture_output=True, text=True, check=True).stdout
for f in g("diff", "--name-only", own + "~1", own).split():
    d = g("diff", own + "~1", own, "--", f).splitlines()
    new = [l[1:] for l in d if l.startswith("+") and not l.startswith("+++")]
    have = set(open(f, errors="replace").read().splitlines()) if os.path.exists(f) else set()
    add = [l for l in new if l not in have]
    if add:
        with open(f, "a") as o:
            o.write("\n".join(add) + "\n")
PY_OWN
git add -- "$@"
git commit -q -m "$msg (re-applied after a reset dropped it)" -- "$@" || true
OWN=$(git rev-parse HEAD)
}
# merge (not rebase): other agents may hold uncommitted edits in this shared tree, which rebase refuses and stash must never touch
# KW-FIX-17 11-05: a conflicted merge is aborted at once (never leaves conflict markers in kit_wave.json on the hub)
preserve_append_logs() {
python3 - <<'PY_APPENDS'
from pathlib import Path
import subprocess
# Only shared append journals are eligible. In-place edits, deletions and all
# other files remain dirty, so an overlapping upstream merge still refuses.
paths = ("lanes/COORD-REVIEW-QUEUE.md", "lanes/GEOM-REVIEW.md", "HANDOFF.md",
         "CODEX-LOG.md", "autopilot/kit_wave_pending.tsv")
keep = []
for name in paths:
    old = subprocess.run(["git", "show", "HEAD:" + name], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    f = Path(name)
    if old.returncode or not f.is_file():
        continue
    new = f.read_bytes()
    if new != old.stdout and new.startswith(old.stdout):
        keep.append(name)
if keep:
    subprocess.run(["git", "add", "--", *keep], check=True)
    subprocess.run(["git", "commit", "-q", "-m", "coord: preserve concurrent append-only journals", "--", *keep], check=True)
PY_APPENDS
}
# KW-FIX-25 11-06: on the hub (the host that runs autopilot) RELEASE_TREE.md is generated output of release_tree_plan.py and
# the coordinator commits it from its own checkout; a dirty copy there made every merge here refuse, 22:22-23:0x. Discard it
# on the hub only: on any other host it may be the coordinator's hand edit. A path this call committed is already clean.
discard_generated() {
if [ -f "$HOME/.config/systemd/user/autopilot.service" ]; then
  # COORD 11-12: lanes/STALE.tsv is generated by tools/stale_list.py (stale_cron.sh, hourly) the same way; a dirty copy
  # made lane posts fail ("local changes to lanes/STALE.tsv would be overwritten by merge"), 11-11 23:xx.
  # COORD-COMMIT-SPEED-1 11-13: lanes/VISUAL-QUEUE.tsv is rewritten by kit_wave.py (publish_visual_queue), which commits it only
  # when its body changes; one timed-out commit at 04:25 left it dirty, and hub-git-sync failed on it from 07:05. Discard; the
  # next kit_wave tick rewrites and commits it.
  for g in RELEASE_TREE.md lanes/STALE.tsv lanes/VISUAL-QUEUE.tsv; do
    git diff --quiet -- "$g" || git checkout -q -- "$g"
  done
fi
}
# REPO-STATE-1 11-14: replay only this call's own changes (OWN~1..OWN) onto origin/$B in a private index and push it.
replay_own() {
[ -n "$OWN" ] || return 1
git fetch -q origin "$B" || return 1
R=$(OWN="$OWN" UP="origin/$B" MSG="$msg (replayed own files on origin)" python3 -I - <<'PY_REPLAY'
import os, subprocess as S, sys, tempfile
own, up, msg = os.environ["OWN"], os.environ["UP"], os.environ["MSG"]
def g(*a, inp=None, env=None):
    r = S.run(["git", *a], input=inp, capture_output=True, env=env)
    if r.returncode: raise SystemExit(1)
    return r.stdout
def blob(rev, f):
    r = S.run(["git", "cat-file", "blob", f"{rev}:{f}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None
files = [f for f in g("diff", "--name-only", "-z", own + "~1", own).decode().split("\0") if f]
put = {}
for f in files:
    base, mine, cur = blob(own + "~1", f), blob(own, f), blob(up, f)
    if mine is None: raise SystemExit(1)                     # deletions are not replayed
    if cur == base or cur == mine: put[f] = mine; continue
    if base is not None and mine.startswith(base) and cur is not None:
        add = mine[len(base):]
        if add and add in cur: put[f] = cur; continue          # already carried upstream
        put[f] = cur + (b"" if cur.endswith(b"\n") or not cur else b"\n") + add; continue
    if base is None and cur is not None and mine.startswith(cur): put[f] = mine; continue
    raise SystemExit(1)                                      # an in-place edit that upstream also changed: no replay
with tempfile.TemporaryDirectory() as d:
    env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "index"))
    g("read-tree", up, env=env)
    for f, data in put.items():
        h = g("hash-object", "-w", "--stdin", inp=data).decode().strip()
        mode = "100755" if os.access(f, os.X_OK) else "100644"
        g("update-index", "--add", "--cacheinfo", f"{mode},{h},{f}", env=env)
    tree = g("write-tree", env=env).decode().strip()
    if tree == g("rev-parse", up + "^{tree}").decode().strip():
        print(g("rev-parse", up).decode().strip()); sys.exit(0)  # nothing left to carry
    print(g("commit-tree", tree, "-p", up, "-m", msg).decode().strip())
PY_REPLAY
) || return 1
[ -n "$R" ] || return 1
if on_origin "$R" || git push -q origin "$R:refs/heads/$B"; then
  git fetch -q origin "$B" || true; OWN="$R"; return 0
fi
return 1
}
succeed() { echo "PUSHED $( [ -n "$OWN" ] && git rev-parse "$OWN" || git rev-parse HEAD )"; exit 0; }
LASTWHY="no attempt completed"; E=$(mktemp); trap 'rm -f "$E"' EXIT
firstline() { head -c 300 "$E" | tr '\n' ' '; }
on_origin() { git merge-base --is-ancestor "$1" "origin/$B" 2>/dev/null; }
# done when origin holds our own commit; with no commit of our own, when origin holds HEAD (our lines, if committed by
# preserve_append_logs here or by an earlier holder, are in HEAD)
done_now() { if [ -n "$OWN" ]; then on_origin "$OWN"; else on_origin "$(git rev-parse HEAD)"; fi; }
for i in 1 2 3; do
  t=$(now); flock 8; W8=$(echo "$W8+$(now)-$t" | bc)
  # coalesce: an earlier pusher already carried our commit
  if [ -n "$OWN" ] && git fetch -q origin "$B" && on_origin "$OWN"; then tlog coalesced; succeed; fi
  t=$(now); flock 9; W9=$(echo "$W9+$(now)-$t" | bc)
  ok=0
  merged=1
  discard_generated
  if ! preserve_append_logs 2>"$E"; then LASTWHY="preserving concurrent append journals failed: $(firstline)"
  elif ! git fetch -q origin "$B" 2>"$E"; then LASTWHY="fetch of origin/$B failed: $(firstline)"
  elif ! git merge -q --no-edit "origin/$B" >"$E" 2>&1; then
    LASTWHY="merge of origin/$B refused in the shared tree (dirty files overlap upstream changes?): $(firstline)"
    git merge --abort 2>/dev/null || true; merged=0
  elif ! restore_own "$@" 2>"$E"; then LASTWHY="re-applying own commit after merge failed: $(firstline)"
  else ok=1; fi
  P=$(git rev-parse HEAD)
  flock -u 9
  if [ $ok = 0 ] && [ $merged = 0 ] && [ -n "$OWN" ]; then
    t=$(now)
    if replay_own 2>"$E"; then TP=$(echo "$TP+$(now)-$t" | bc); if done_now; then tlog replayed; succeed; fi
    else LASTWHY="$LASTWHY; replay of own files onto origin/$B failed (an in-place edit upstream also changed, a deletion, or fetch/push failed): $(firstline)"; fi
    TP=$(echo "$TP+$(now)-$t" | bc)
  fi
  if [ $ok = 1 ]; then
    if done_now; then tlog coalesced; succeed; fi
    t=$(now)
    if git push -q origin "$P:refs/heads/$B" 2>"$E"; then
      TP=$(echo "$TP+$(now)-$t" | bc)
      git fetch -q origin "$B" || true
      if done_now || { [ -z "$OWN" ] && on_origin "$P"; }; then tlog pushed; succeed; fi
    else
      LASTWHY="push to origin/$B rejected: $(firstline)"
      TP=$(echo "$TP+$(now)-$t" | bc)
    fi
  fi
  flock -u 8
  sleep $((${COORD_COMMIT_BACKOFF:-3} * i * i))
done
tlog FAILED
echo "FAILED after 3 attempts: $LASTWHY" | tee /dev/stderr; exit 1
