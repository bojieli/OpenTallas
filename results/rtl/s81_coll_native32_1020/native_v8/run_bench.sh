#!/bin/bash
# $1 = mutant 0..4
OT_COLL_NATIVE32=1 OT_COLL_NATIVE32_OFF=1 bash tools/xdie_s81/coll_safe4_boundary.sh runs/m$1 $1 > m$1.log 2>&1; rc=$?; cat runs/m$1/run.log >> m$1.log 2>/dev/null; echo "bench rc $rc" >> m$1.log; exit $rc
