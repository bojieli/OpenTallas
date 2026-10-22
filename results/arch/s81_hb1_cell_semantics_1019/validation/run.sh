#!/bin/bash
set -u
mkdir run01 || exit 99
exec > >(tee run01/run.log) 2>&1
hostname
free -b
df -B1 .
command -v iverilog
iverilog -V 2>&1 | head -4
sha256sum /usr/bin/iverilog /usr/bin/vvp
status=0
for kind in positive mut_polarity mut_priority mut_comb; do
  proj=functional_projection.v
  if [ "$kind" != positive ]; then proj=validation/$kind.v; fi
  /usr/bin/time -v iverilog -g2012 -s tb -o run01/$kind.vvp validation/official_reference.v "$proj" validation/tb.v > run01/$kind.build.log 2>&1
  rc=$?
  cat run01/$kind.build.log
  if [ "$rc" != 0 ]; then status=1; continue; fi
  /usr/bin/time -v vvp run01/$kind.vvp > run01/$kind.log 2>&1
  rc=$?
  echo "$kind exit $rc"
  cat run01/$kind.log
  if [ "$kind" = positive ]; then
    if [ "$rc" != 0 ] || ! grep -q CELL_PROJECTION_PASS run01/$kind.log; then status=1; fi
  else
    if [ "$rc" = 0 ] || ! grep -Eq '(COMB_MISMATCH|ASR_MISMATCH|HQ_MISMATCH)' run01/$kind.log; then status=1; fi
  fi
done
echo "VALIDATION_EXIT $status"
exit "$status"
