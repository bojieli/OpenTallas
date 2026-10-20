#!/bin/bash
# S81-DIE10 10-20: NATIVE forwarded-clock re-export of all 14 dsfd_dvrlyh families from their ORIGINAL archived routed
# ODB/SPEF (closed_archive, sha-identical to the agidock originals), main exporter tools/tt_views/view_export.py
# (sha 578418117d35..., = Codex's reviewed exporter), job replay of each job's own sign-off sequence, checked against the
# job verdict (TT setup / FF hold, 0.05 ps), --forwarded-clock ck:ck_o (polarity derived from Liberty, never relabelled).
# No ODB mutation (PG of late CTS buffers stays as routed: separate S81.STA.PG obligation).
# usage: run_native14.sh [FAMILY...]
L=$(cd $(dirname $0) && pwd); cd $L
FAMS=${*:-$(ls -d dsfd_dvrlyh_* | xargs)}
rc_all=0
for M in $FAMS; do
  O=$L/$M; rm -rf $O/views $O/tmp; mkdir -p $O/views $O/tmp
  python3 $L/view_export.py --orfs-dir $O/orfs --name $M --out $O/views --corners ss,ff,tt --forwarded-clock ck:ck_o \
    --job-json $O/job.json --src $L/src41e --cl-dir $O/cl --job-extra-sdc $O/w18_extra.sdc --require-check \
    --image openroad/orfs:asap7lock --tmp-dir $O/tmp --pin-only-tech > $O/export_driver.log 2>&1
  rc=$?; echo "NATIVE_EXPORT $M rc=$rc $(tail -n 1 $O/export_driver.log)" | tee -a $L/native14.log
  [ $rc -eq 0 ] || rc_all=1
  rm -rf $O/tmp
done
exit $rc_all
