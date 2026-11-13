#!/bin/bash
# bind.sh SHA12 : strict bind + lane latency of plan_frame_spine_<SHA12> (pattern events/s81_ready12bA_1112/run_r12bA_dst.sh)
# tree bsrc_fs = hardlinks of src_s81_7073 (main 7073a6b4a5 + KIT-OPS-1 overlays) with REAL copies of the candidate plan / sidecars
set -u; set -o pipefail; cd /; export PYTHONDONTWRITEBYTECODE=1
V=/srv/opentallas-scratch3/claude/frame-forms-1/vol; W=/srv/opentallas-scratch3/claude/wt/frame-forms-1; S=$V/src_s81_7073; D=$V/bsrc_fs; OUT=$V/out_fs
SEED=/srv/opentallas-scratch2/claude/kit-ops-1/s81_r12bA/out_main_7073a6b4a5_b; AB0=/srv/opentallas-scratch2/claude/kit-ops-1/s81_r12bA/asbuilt_kitops1_7073a6b4a5.json; AB=$V/asbuilt_fs.json
PL=$W/physical/die_plan/s81/plan_frame_spine_$1.json; P=physical/die_plan/s81/plan_r12bA6.json
test -s $PL || { echo "no plan $PL"; exit 3; }; test ! -e $D || { echo "REFUSE $D"; exit 3; }; test ! -e $OUT || { echo "REFUSE $OUT"; exit 3; }
cp -al $S $D || exit 4
for f in $P physical/die_plan/s81/plan_h2_2249.json; do cp --remove-destination $PL $D/$f; done
cp --remove-destination $V/r2_side_psplit_all.c2.json $D/physical/die_plan/s81/h2_2249/landed_sidecar_h2_psplit_all.json
cp --remove-destination $V/r2_side_psplit_all_gear.c2.json $D/physical/die_plan/s81/h2_2249/landed_sidecar_h2_psplit_all_gear.json
python3 -I -c "import json,sys; a=json.load(open(sys.argv[1])); a[\"base\"]=sys.argv[3]; a[\"note\"]=\"FRAME-FORMS-1-VOL: kit-ops-1 asbuilt_kitops1_7073a6b4a5 with base -> \"+sys.argv[3]+\" | \"+str(a.get(\"note\") or \"\"); json.dump(a,open(sys.argv[2],\"w\"),indent=1)" $AB0 $AB $D
echo "plan $(sha256sum < $D/$P | cut -c1-12) asbuilt $(sha256sum < $AB | cut -c1-12)"
mkdir -p $OUT; cp -a $SEED/. $OUT/; rm -rf $OUT/rtl $OUT/bind_report.json $OUT/verify
cd $D || exit 9
nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $OUT --strict > $V/bind.log 2>&1; rc=$?; echo BIND_RC=$rc
grep -v "PLAN-PACKAGE WARNING\|TAP-RADIUS-TARGET" $V/bind.log | tail -n 3 | cut -c1-400
[ $rc = 0 ] || exit 5
mkdir -p $V/lc; python3 -I -B $W/tools/die_plan/lane_asbuilt_latency.py $OUT $D/$P --asbuilt $AB --pricing as-bound --tsv $V/lc/fs.tsv --json $V/lc/fs.json > $V/lc/fs.log 2>&1; rc=$?
echo LATCHECK_RC=$rc; tail -n 2 $V/lc/fs.log | cut -c1-400
echo BIND_SH_DONE
