#!/bin/bash
# neg.sh NEWRUN OLDRUN: replay NEWRUN's replay vectors (new-kit measured descriptors + calendar) on the OLD TYPE-SAFE-5
# kit static bench OLDRUN/obj_static (copies; NEWRUN untouched).  Expected: positive cases FAIL.
set -u
NEW=$1; OLD=$2; D=/srv/opentallas-scratch2/claude/s81-bfasb-1111; FIX=/srv/opentallas-scratch2/claude/tok-verify-1/fixtures/L0
cd $OLD || exit 4; mkdir -p replay
for n in full tail router; do d=$OLD/replay/$n
  [ -d $d ] || { mkdir -p $d; for f in $NEW/replay/$n/*; do case $(basename $f) in run.log|check.json|check.log) ;; *) ln $f $d/ ;; esac; done; }
  rm -f $d/ARGS; sed "s#$NEW/replay/$n#$d#" $NEW/replay/$n/ARGS > $d/ARGS
  ./obj_static/Vtb_s81dv_frame $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR=$d#" $d/ARGS) > $d/run.log 2>&1
  python3 -I $D/pyrun.py $D/code/tools/s81_dv/layer_prog/xs_place.py check --dir $d --log $d/run.log --fixtures $FIX > $d/check.log 2>&1
  echo "OLDKIT $n $(tail -n 1 $d/check.log)"; grep -m3 -E "FAULT|fault|PLAN_|MISMATCH" $d/check.log | cut -c1-200
  grep -m4 -iE "fault|BFP_BAD" $d/run.log | grep -v "^END" | cut -c1-200
done
