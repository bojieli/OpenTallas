#!/bin/bash
# S81-R12BA-FIN 11-12: ready12b-A final = B1-B3 + B3b + B5 (kit source) + B6 (kit dest, 19 LATCHECK-1 lanes) + switch ON.
# Code tree bsrc_r12bA_dst: hardlinks of bsrc_r12bA_m bulk, REAL copies of rtl/ and tools/ (wt/s81-r12ba-fin 9489114321 =
# 51f3e29a10 + stage commits only); plan files written with --remove-destination.  Out seeded from out_r12bA_m (elab reuse).
# Steps: G0, strict bind, LATCHECK-1 CLI (must be 0), then copy OUT -> OUT_main and launch the main-tools verify as its own
# ot-heavy job, then the merged-tools verify here.  Memory: asbuilt lint_jobs 6 x ~23 GB verilator + ~26 GB python.
set -u
O=/srv/opentallas-scratch2/claude/s81-leaf-floor-2; F=/srv/opentallas-scratch2/claude/s81-r12ba-fin; W=/srv/opentallas-scratch2/claude/wt/s81-r12ba-fin
S=$O/bsrc_r12bA_m; D=$F/bsrc_r12bA_dst; OUT=$F/out_r12bA_dst; P=physical/die_plan/s81/plan_r12bA6.json; AB=$O/asbuilt_ist.json
export PYTHONDONTWRITEBYTECODE=1; set -o pipefail
test ! -e $D || { echo "REFUSE $D exists"; exit 3; }; test ! -e $OUT || { echo "REFUSE $OUT exists"; exit 3; }
mkdir -p $D
for d in $(ls -A $S); do case $d in rtl) cp -a $S/rtl $D/ ;; tools) cp -a $W/tools $D/ ;; *) cp -al $S/$d $D/ ;; esac; done
cp --remove-destination $F/s6_kdst.json $D/$P
cp --remove-destination $F/s6_kdst.json $D/physical/die_plan/s81/plan_h2_2249.json
echo "tools $(git -C $W rev-parse --short HEAD) plan $(sha256sum < $D/$P | cut -c1-12) asbuilt $(sha256sum < $AB | cut -c1-12)"
cd $D || exit 9
nice -n 10 python3 -I -B tools/die_plan/check.py $P --out $F/g0dst --quiet > $F/g0dst.log 2>&1; echo G0_RC=$?
mkdir -p $OUT; cp -a $O/out_r12bA_m/. $OUT/; rm -rf $OUT/rtl $OUT/bind_report.json $OUT/verify
nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $OUT --strict > $F/bind_dst.log 2>&1; rc=$?; echo BIND_RC=$rc
[ $rc = 0 ] || exit 4
python3 -I -B $F/lc/lane_asbuilt_latency.py $OUT $D/$P --asbuilt $AB --pricing as-bound --tsv $F/lc/dst.tsv --json $F/lc/dst.json > $F/lc/dst.log 2>&1; rc=$?
echo LATCHECK_RC=$rc; tail -n 1 $F/lc/dst.log | cut -c1-300
[ $rc = 0 ] || exit 5
cp -a $OUT $F/out_r12bA_dst_main && echo COPY_MAIN_DONE
nohup setsid ot-heavy --mem 200 -- bash $F/bin/run_verify_main_dst.sh > $F/verify_main_dst.otrun.log 2>&1 < /dev/null &
nice -n 5 python3 -I -B tools/die_plan/bind.py verify $P --asbuilt $AB --out $OUT --strict > $F/verify_dst.log 2>&1; echo VERIFY_RC=$?
echo RUN_DST_DONE
