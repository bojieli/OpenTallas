#!/bin/bash
# prep.sh WT OUT : base (origin/main d44v) + new (worktree d44v) unzipped plan copies with the missing pins tables filled
set -e; W=$1; O=$2; rm -rf $O/base $O/new; mkdir -p $O/base $O/new
cd $W
git archive origin/main physical/die_plan/hbm/plan_of_record/d44v | tar -x -C $O/base --strip-components=5
cp -r physical/die_plan/hbm/plan_of_record/d44v/. $O/new/
for d in base new; do (cd $O/$d; find . -name "*.gz" -print0 | xargs -0 gunzip -f)
  for f in $(ls /srv/opentallas-scratch3/claude/die-hbm-82/clkscan/plan/cores); do [ -e $O/$d/cores/$f ] || cp /srv/opentallas-scratch3/claude/die-hbm-82/clkscan/plan/cores/$f $O/$d/cores/; done; done
echo PREP_OK
