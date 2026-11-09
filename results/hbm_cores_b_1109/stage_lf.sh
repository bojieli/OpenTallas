#!/bin/bash
# stage wave/src_lf = hard-link copy of realpath(wave/src), bind.py (LeafFollow merged) + legacy_gate.py (G2 advisory) replaced.
# args: <merged bind.py> <legacy_gate.py>
set -eu
W=/srv/opentallas-scratch2/claude/qct11/wave
R=$(readlink -f $W/src)
NEW=${R}_lf
test -e "$NEW" && { echo "EXISTS $NEW"; exit 3; }
cp -al "$R" "$NEW"
test ! -L "$NEW"
D=$NEW/tools/die_plan
chmod u+w "$D"
for f in bind.py legacy_gate.py; do
  rm -f "$D/$f"
done
cp "$1" "$D/bind.py"; cp "$2" "$D/legacy_gate.py"
chmod 444 "$D/bind.py" "$D/legacy_gate.py"
chmod a-w "$D"
if [ -L $W/src ]; then ln -sfn "$NEW" $W/src_lf; fi
md5sum "$NEW/tools/die_plan/bind.py" "$NEW/tools/die_plan/legacy_gate.py"
readlink -f $W/src_lf
# originals still intact
md5sum "$R/tools/die_plan/bind.py" "$R/tools/die_plan/legacy_gate.py"
