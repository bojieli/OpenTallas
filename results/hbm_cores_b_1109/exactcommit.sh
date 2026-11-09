#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/qct12/repo
B=0de58b0ef8f762061b3888af0bd4e7412a46a43f
export GIT_INDEX_FILE=/srv/opentallas-scratch2/claude/qct12/exact/index
rm -f $GIT_INDEX_FILE
git read-tree $B
E=/srv/opentallas-scratch2/claude/qct12/exact
while read path name; do
  sha=$(git hash-object -w "$E/$name")
  mode=$(git ls-files -s -- "$path" | awk '{print $1}'); test -n "$mode"
  git update-index --cacheinfo "$mode,$sha,$path"
  echo "$mode $sha $path"
done <<LIST
physical/die_plan/qwen_compute/qc_start_1108/plan_start.py plan_start.py
tools/die_plan/bind.py bind.py
tools/die_plan/legacy_gate.py legacy_gate.py
rtl/qwen_sys/dvm_20261014/ot_qfd_xs_leaf_fo32.sv ot_qfd_xs_leaf_fo32.sv
LIST
T=$(git write-tree)
unset GIT_INDEX_FILE
C=$(git commit-tree $T -p $B -m "QC-TYPES-12: exact source of the QC v4nS wave tree (src_lf)

Composition: origin/main 685b58b80c3 + ctlm a1bd215ec93 + hc3 b9065f3dddc (= compose a5621488408 reconstruction,
verified file by file against the staged tree) + HC3 flat-state bf29a7a50e + constructor cbd4c6adfd9 +
LeafFollow fea7df0c0a6 + G2 advisory 958a7d6d7fe (only these four files replaced). Launch queue_src identity
for the QC plan_qc53v4nS switch; tree equals staged wave/src_lf except stale untracked results/ data.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
echo commit $C tree $T
git branch -f claude/qc-types-12-wave-src-1108 $C
git push -q origin claude/qc-types-12-wave-src-1108 2>&1 | tail -2
git ls-tree -r $C | awk '{print $3, $4}' > ../lf/exact.tree
git rev-parse claude/qc-types-12-wave-src-1108
