#!/bin/bash
set -euo pipefail
lane=/srv/opentallas-scratch/claude/codex-s81-tx-clock-fullpair-2215
frozen=47962969f5104ac62d0c9868caff013319cfda5f
cd "$lane"
if [ ! -d repo ]; then git clone --shared --no-checkout /srv/opentallas-scratch/claude/git-mirror/OpenTallas.git repo; fi
[ "$(git -C repo rev-parse --show-toplevel)" = "$lane/repo" ]
git -C repo fetch "$lane/main.bundle" refs/remotes/origin/main
[ "$(git -C repo rev-parse FETCH_HEAD)" = "$frozen" ]
printf '%s\n' "$frozen" > out/frozen_main.txt
sha256sum candidate/clock_spine.tcl main.bundle > out/input.sha256
for side in baseline candidate; do
 mkdir -p "$side/source"
 git -C repo archive "$frozen" | tar -x -C "$side/source"
 if [ "$side" = candidate ]; then cp candidate/clock_spine.tcl candidate/source/physical/common_flow/clock_spine.tcl; fi
 sha256sum "$side/source/physical/common_flow/clock_spine.tcl" > "out/$side.clock_spine.sha256"
 for suite in closure_loop ref_tile hier_contract tt_views; do
  set +e
  (cd "$side/source" && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "tools/$suite") > "out/$side.$suite.log" 2>&1
  rc=$?
  set -e
  printf '%s %s rc=%s\n' "$side" "$suite" "$rc" | tee -a out/status
 done
done
touch out/DONE
