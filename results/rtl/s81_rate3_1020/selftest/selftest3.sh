#!/bin/bash
set -u; D=/srv/opentallas-scratch/claude/s81-rate3; cd $D/root; export PYTHONDONTWRITEBYTECODE=1
for M in default release; do
  if [ $M = release ]; then export OT_XS_QPAIRS=12 OT_XS_GU_MERGE=1 OT_XS_CAL_SEGMENT=1 OT_XS_TOPO=1 OT_XS_PROP=1; fi
  rm -rf $D/out/selftest_$M; timeout 1800 python3 tools/s81_dv/layer_prog/xs_field_calendar.py selftest --out $D/out/selftest_$M > $D/out/selftest_$M.log 2>&1; echo "SELFTEST $M rc=$? $(tail -1 $D/out/selftest_$M.log | cut -c1-300)"
done
