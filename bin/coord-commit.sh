#!/bin/bash
# usage: coord-commit.sh "message" file1 [file2 ...]   (paths relative to ~/coord) -- serialised commit+push of coord/state
set -e
cd /home/ubuntu/coord
msg="$1"; shift
exec 9>/home/ubuntu/coord/.coord.lock
flock 9
git add -- "$@"
git commit -q -m "$msg" -- "$@" || true
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
if [ -f "$HOME/.config/systemd/user/autopilot.service" ] && ! git diff --quiet -- RELEASE_TREE.md; then
  git checkout -q -- RELEASE_TREE.md
fi
}
for i in 1 2 3 4 5; do discard_generated; preserve_append_logs && git fetch -q origin coord/state && { git merge -q --no-edit origin/coord/state || { git merge --abort 2>/dev/null; false; }; } && git push -q origin coord/state && exit 0; sleep 3; done
echo "coord push failed" >&2; exit 1
