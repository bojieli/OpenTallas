#!/bin/bash
set -u
mkdir run02 || exit 99
exec > >(tee run02/run.log) 2>&1
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
  /usr/bin/time -v iverilog -g2012 -s tb -o run02/$kind.vvp validation/official_reference.v "$proj" validation/tb.v > run02/$kind.build.log 2>&1
  rc=$?
  cat run02/$kind.build.log
  if [ "$rc" != 0 ]; then status=1; continue; fi
  /usr/bin/time -v vvp run02/$kind.vvp > run02/$kind.log 2>&1
  rc=$?
  echo "$kind exit $rc"
  cat run02/$kind.log
  if [ "$kind" = positive ]; then
    if [ "$rc" != 0 ] || ! grep -q CELL_PROJECTION_PASS run02/$kind.log; then status=1; fi
  else
    if [ "$rc" = 0 ] || ! grep -Eq '(COMB_MISMATCH|ASR_MISMATCH|HQ_MISMATCH)' run02/$kind.log; then status=1; fi
  fi
done
iverilog -g2012 -s tb -o run02/fourstate.vvp validation/official_reference.v functional_projection.v validation/tb_fourstate.v >run02/fourstate.build.log 2>&1
rc=$?; cat run02/fourstate.build.log
if [ "$rc" = 0 ]; then /usr/bin/time -v vvp run02/fourstate.vvp >run02/fourstate.log 2>&1; echo "fourstate exit $?";cat run02/fourstate.log; else status=1; fi
echo "VALIDATION_EXIT $status"
exit "$status"
