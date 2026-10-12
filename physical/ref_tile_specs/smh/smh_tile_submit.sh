#!/bin/bash
# [smmv-b/smt] one-command submit of the SM tile clusters (smh_tile_eg_ref / smh_tile_wg_ref) once their two open
# children are CLOSED with child_lint (c)+(f) clean:
#   pt_w  smh_pt_w_ref_p45h-r1-6332f4e44  (views -> physical/ref_tile/smh_pt_w_ref_p45h/views)
#   xs    smh_xs_ref_p50x-r1-0bce85cc9    (views -> physical/ref_tile/smh_xs_ref_p50x/views; exact io_tcl pins for MX)
# Merges their closure records, re-generates both kits on the real views (sizes, pins on track per orientation, spine
# child-insertion targets), lints, commits, writes the job specs and drops them into the closure-loop intake.
# Usage: bash physical/ref_tile_specs/smh/smh_tile_submit.sh   (run from the claude/el1011-hbm-smt worktree)
set -euo pipefail
WT=${WT:-/home/ubuntu/wt/el1011-hbm-smt}
cd "$WT"
J=~/.local/state/closure_loop/jobs
for j in smh_pt_w_ref_p45h-r1-6332f4e44 smh_xs_ref_p50x-r1-0bce85cc9; do
  st=$(python3 -c "import json;print(json.load(open('$J/$j.json'))['status'])")
  [ "$st" = CLOSED ] || { echo "BLOCKED: $j is $st"; exit 2; }
done
# gate-only placeholders (hand pt_w view / xs LEF with planned pins) must go before the records land
rm -rf physical/ref_tile/smh_pt_w_ref_p45h/views physical/ref_tile/smh_xs_ref_p50x/views
git checkout -- physical/ref_tile 2>/dev/null || true
git fetch -q origin
git merge -q --no-edit origin/claude/el1011-hbm-smt   # the loop auto-merges xs p50x's record here
git merge -q --no-edit origin/main
for b in smh_pt_w_ref_p45h-r1-6332f4e44 smh_xs_ref_p50x-r1-0bce85cc9; do
  if git rev-parse -q --verify "origin/codex/closure-record-$b" >/dev/null; then git merge -q --no-edit "origin/codex/closure-record-$b"; fi
done
for v in physical/ref_tile/smh_pt_w_ref_p45h/views/ot_hbm_accel_smh_pt_w physical/ref_tile/smh_xs_ref_p50x/views/ot_hbm_accel_smh_xs; do
  [ -s "$v/$(basename $v).lef" ] || { echo "BLOCKED: no view $v (closure record not merged yet)"; exit 2; }
  python3 tools/hier_contract/child_lint.py "$v/$(basename $v).lef" --libs "$v" | tail -1 | grep -q '^PASS' \
    || { echo "BLOCKED: child_lint FAIL on $v"; exit 2; }
done
python3 physical/ref_tile_specs/smh/mk_smh_tile_cluster.py
for v in eg wg; do
  python3 tools/ref_tile/ref_tile.py gen physical/ref_tile_specs/smh/smh_tile_${v}_ref.json | tee /tmp/smt_gen_$v.log
  ! grep -q 'REF_TILE FAIL' /tmp/smt_gen_$v.log || { echo "BLOCKED: gen FAIL ($v)"; exit 2; }
  python3 tools/ref_tile/pre_route_gate.py physical/ref_tile/smh_tile_${v}_ref | tail -1 | grep -qv FAIL \
    || { echo "BLOCKED: local gate FAIL ($v)"; exit 2; }
done
git add physical/ref_tile_specs/smh physical/ref_tile/smh_tile_eg_ref physical/ref_tile/smh_tile_wg_ref
git commit -q -m "[smmv-b/smt] SM tile cluster kits eg/wg on the closed pt_w p45h + xs p50x views

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || true
C=$(git rev-parse --short=9 HEAD)
for v in eg wg; do python3 tools/ref_tile/ref_tile.py job physical/ref_tile_specs/smh/smh_tile_${v}_ref.json --commit $C; done
git add physical/ref_tile/smh_tile_eg_ref/job.json physical/ref_tile/smh_tile_wg_ref/job.json
git commit -q -m "[smmv-b/smt] SM tile cluster jobs eg/wg @$C

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin HEAD:claude/el1011-hbm-smt
for v in eg wg; do
  n=$(python3 -c "import json;print(json.load(open('physical/ref_tile/smh_tile_${v}_ref/job.json'))['name'])")
  cp physical/ref_tile/smh_tile_${v}_ref/job.json /tmp/claude-review-20261003/closure_jobs/$n.json
  echo "SUBMITTED $n"
  echo "$(TZ=America/Los_Angeles date +'%m-%d %H:%M') [smmv-b/smt] SUBMITTED $n" >> /home/ubuntu/claude-takeover-20261007/el1011-hbm-smh.log
done
