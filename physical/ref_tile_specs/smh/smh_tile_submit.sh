#!/bin/bash
# [smmv-b/smt] one-command submit of the SM tile clusters (smh_tile_eg_ref / smh_tile_wg_ref) once their two open
# children are CLOSED with child_lint (c)+(f) clean:
#   pt_w  smh_pt_w_ref_p45h-r1-6332f4e44  (views -> physical/ref_tile/smh_pt_w_ref_p45h/views)
#   xs    smh_xs_ref_p50m/p45m-r1-b749b74bf (mirror-safe: H face pins M4 only) or smh_xs_ref_p40x-r1-9315ade96 (regen on main >= eb642d870 after c2250fec8 GRT-0116) or smh_xs_ref_t40-r1-c2250fec8 (exact io_tcl pins, needed for the leaf-1 MX copy)
# Merges their closure records, re-generates both kits on the real views (sizes, pins on track per orientation, spine
# child-insertion targets), lints, commits, writes the job specs and drops them into the closure-loop intake.
# Usage: bash physical/ref_tile_specs/smh/smh_tile_submit.sh   (run from the claude/el1011-hbm-smt worktree)
set -euo pipefail
WT=${WT:-/home/ubuntu/wt/el1011-hbm-smt}
cd "$WT"
J=~/.local/state/closure_loop/jobs
st() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$J/$1.json" 2>/dev/null || echo MISSING; }
[ "$(st smh_pt_w_ref_p45h-r1-6332f4e44)" = CLOSED ] || { echo "BLOCKED: pt_w p45h not CLOSED"; exit 2; }
XS="${SMT_XS_OVERRIDE:-}"; XJ="${SMT_XJ_OVERRIDE:-}"   # coordinator 10-12: closed xs p50/p45 @0fbf9bc20 (M6 grant, r25gq v11)
[ -n "$XS" ] || for j in smh_xs_ref_p50m-r3-29a3f8638 smh_xs_ref_p45m-r3-29a3f8638 smh_xs_ref_p50m-r2-a3b3345d2 smh_xs_ref_p45m-r2-a3b3345d2 smh_xs_ref_p50m-r1-b749b74bf smh_xs_ref_p45m-r1-b749b74bf smh_xs_ref_p40x-r1-9315ade96 smh_xs_ref_t40-r1-c2250fec8; do [ "$(st $j)" = CLOSED ] && { XS=${j%-r[0-9]-*}; XJ=$j; break; }; done
[ -n "$XS" ] || { echo "BLOCKED: no exact-pin xs closed (p40x: $(st smh_xs_ref_p40x-r1-9315ade96), t40: $(st smh_xs_ref_t40-r1-c2250fec8))"; exit 2; }
export SMT_XS_KIT=$XS
# gate-only xs placeholders must go before the record lands
[ -n "${SMT_XS_OVERRIDE:-}" ] || rm -rf physical/ref_tile/smh_xs_ref_p50x/views physical/ref_tile/smh_xs_ref_p40x/views physical/ref_tile/smh_xs_ref_t40/views
git checkout -- physical/ref_tile 2>/dev/null || true
git fetch -q origin
git merge -q --no-edit origin/claude/el1011-hbm-smt   # the loop auto-merges the xs record here
git merge -q --no-edit origin/main
for b in smh_pt_w_ref_p45h-r1-6332f4e44 $XJ; do
  if git rev-parse -q --verify "origin/codex/closure-record-$b" >/dev/null; then git merge -q --no-edit "origin/codex/closure-record-$b"; fi
done
for v in physical/ref_tile/smh_pt_w_ref_p45h/views/ot_hbm_accel_smh_pt_w physical/ref_tile/$XS/views/ot_hbm_accel_smh_xs; do
  [ -s "$v/$(basename $v).lef" ] || { echo "BLOCKED: no view $v (closure record not merged yet)"; exit 2; }
  cl=$(python3 tools/hier_contract/child_lint.py "$v/$(basename $v).lef" --libs "$v" || true); grep -q '^PASS' <<<"$cl" \
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
git commit -q -m "[smmv-b/smt] SM tile cluster kits eg/wg on the closed pt_w p45h + xs $XS views

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
