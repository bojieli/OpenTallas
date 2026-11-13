#!/bin/bash
# DIE-S81-88 11-13: ready12b-A + B5 (kit-source table refresh, 22 lanes) + kit_source_station_pricing ON (COORD 16:2x ruling).
# Tools = wt/s81-lfcs-merge 51f3e29a10 (s81-lfcs-depth-gate 0c0dcd1780 + origin/main 91a4101f18, has QC-BIND-IST-PAD 4b6dee512d).
# Code tree bsrc_r12bA_ist: hardlinks of bsrc_r12bA_m bulk, REAL copies of rtl/ (same rtl as m2) and tools/; plan files written
# with --remove-destination (links broken).  Out dir out_r12bA_ist seeded from out_r12bA_m (elab reuse, as m2).
set -u
O=/srv/opentallas-scratch2/claude/s81-leaf-floor-2; M=/srv/opentallas-scratch2/claude/wt/s81-lfcs-merge; R=$O/r12b
S=$O/bsrc_r12bA_m; D=$O/bsrc_r12bA_ist; OUT=$O/out_r12bA_ist; P=physical/die_plan/s81/plan_r12bA5.json; AB=$O/asbuilt_ist.json
export PYTHONDONTWRITEBYTECODE=1; set -o pipefail
test ! -e $D || { echo "REFUSE $D exists"; exit 3; }; test ! -e $OUT || { echo "REFUSE $OUT exists"; exit 3; }
mkdir -p $D
for d in $(ls -A $S); do case $d in rtl) cp -a $S/rtl $D/ ;; tools) cp -a $M/tools $D/ ;; *) cp -al $S/$d $D/ ;; esac; done
cp --remove-destination $R/s5_ksrc.json $D/$P
cp --remove-destination $R/s5_ksrc.json $D/physical/die_plan/s81/plan_h2_2249.json
python3 -I - <<'PY' || exit 5
import json
O='/srv/opentallas-scratch2/claude/s81-leaf-floor-2'
a=json.load(open(O+'/asbuilt_lfcs_m.json')); assert 'kit_source_station_pricing' not in a
a['kit_source_station_pricing']=True
json.dump(a,open(O+'/asbuilt_ist.json','w'),indent=1)
PY
echo "tools $(git -C $M rev-parse --short HEAD) plan $(sha256sum < $D/$P | cut -c1-12) asbuilt $(sha256sum < $AB | cut -c1-12)"
cd $D || exit 9
nice -n 10 python3 -I -B tools/die_plan/check.py $P --out $R/g0ist --quiet > $R/g0ist.log 2>&1; echo G0_RC=$?
mkdir -p $OUT; cp -a $O/out_r12bA_m/. $OUT/; rm -rf $OUT/rtl $OUT/bind_report.json $OUT/verify
prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $OUT --strict > $R/bind_ist.log 2>&1; echo BIND_RC=$?
prlimit --as=150000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py verify $P --asbuilt $AB --out $OUT --strict > $R/verify_ist.log 2>&1; echo VERIFY_RC=$?
echo RUN_IST_DONE
