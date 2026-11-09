#!/bin/bash
# HBM-HARD-7: put d44v_epm into the private clone as one commit on main (index plumbing, no checkout) and make the private counter copy.
set -eu
export GIT_SSH_COMMAND='ssh -o ControlPath=none'
S=/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/epm
D=physical/die_plan/hbm/plan_of_record/d44v_epm
cd "$S"
rm -rf staged; mkdir -p "staged/$D/cores"
for f in die_plan.json clock_entries.json core_macros.json core_clock_regions.json ep_mod_1108_event.json ep_mod_1108d_event.json; do cp "o2/$f" "staged/$D/$f"; done
gzip -n -9 "staged/$D/die_plan.json" "staged/$D/clock_entries.json"
cp o2/cores/hfd_ep_static_vc2__427.68x246.24__epmod1108d.json o2/cores/hfd_ep_host_vc__427.68x246.24__epmod1108d.json "staged/$D/cores/"
cat > "staged/$D/README.md" <<'E'
# d44v_epm: HBM plan of record d44v + EP-MOD-1108 + EP-MOD-1108d

Built by HBM-HARD-7, 2026-11-08 (COORD approved), with physical/die_plan/hbm/delta_ep_mod_1108.py at 8bdd1d6452, run on d44v of main ed5be48cd49.

NW_io u_ep_N0 -> hfd_ep_static_vc2, u_host_ep -> hfd_ep_host_vc (the as-built modules), pin tables with RTL directions, same outline and origin. Nothing else changes.
die_plan.json sha256 836809c2858d -> 24d1ff0b505e. Holds only the changed files; use it as the last overlay after d35a, d35b, d35c, d44v.
E
cd repo
M=$(git rev-parse origin/main)
export GIT_INDEX_FILE="$S/index.epm"; rm -f "$GIT_INDEX_FILE"
git read-tree "$M"
(cd "$S/staged"; find physical -type f | sort) | while read -r f; do
  h=$(git hash-object -w "$S/staged/$f")
  git update-index --add --cacheinfo 100644 "$h" "$f"
done
T=$(git write-tree)
unset GIT_INDEX_FILE
C=$(git -c user.name="Bojie Li" -c user.email="$(git log -1 --format=%ae "$M")" commit-tree "$T" -p "$M" -F - <<'E'
HBM plan of record d44v_epm: d44v + EP-MOD-1108 + EP-MOD-1108d

NW_io u_ep_N0 and u_host_ep declare the as-built EP modules, so signed
views of hfd_ep_static_vc2 and hfd_ep_host_vc have a plan design to match.
Changed files only; used as the last overlay after d44v.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
E
)
git update-ref refs/heads/claude/hbm-hard-7-epm-1108 "$C"
echo "commit $C tree $T parent $M"
git diff --stat "$M" "$C" | tail -11 | cut -c1-110
# private counter copy
P="$S/priv"; rm -rf "$P"; mkdir -p "$P/tools" "$P/lanes" "$P/state"
cp ~/coord/tools/release_tree_plan.py "$P/tools/release_tree_plan.py"
cp ~/coord/RETIRED_SIGNOFFS.tsv "$P/" 2>/dev/null || true
cp ~/coord/lanes/COUNT-REVOKED.tsv ~/coord/lanes/COUNT-CREDIT.tsv "$P/lanes/"
grep -n "home()\|/home/ubuntu\|\.local/state\|parent.parent\|coord/" "$P/tools/release_tree_plan.py" | grep -v "^[0-9]*:#" | cut -c1-170
