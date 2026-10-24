#!/bin/bash
# TOKj-KV 10-23: build the KV die-slice vehicle (whole bound top + PHY bench models + tb) with Verilator 5.050.
#   build.sh VDIR OUT [lint]     VDIR = staged vehicle dir (stage_src.sh output: files.f incdirs.f hostside.f src/)
# The staged lists carry the staging host's absolute prefix; they are re-rooted to VDIR here (fleet copies).
set -eu
H=$(cd "$(dirname "$0")" && pwd); V=$(readlink -f $1); O=$(mkdir -p $2 && readlink -f $2); MODE=${3:-build}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P0=$(head -1 $V/files.f | sed 's#/src/.*##')
for f in files.f incdirs.f hostside.f; do sed "s#$P0#$V#g" $V/$f > $O/$f; done
cat > $O/vl.f <<EOF
-Wno-fatal
-Wno-lint
-Wno-style
-Wno-MULTIDRIVEN
-Wno-TIMESCALEMOD
-Wno-PINMISSING
-Wno-MODDUP
--timescale 1ns/1ps
--top-module tb_kvslice
$H/kvs_link_phy_models.sv
$H/qkd_hbm3e_phy_pc4_bench.sv
$H/tb_kvslice.sv
EOF
cat $O/hostside.f $O/files.f $O/incdirs.f >> $O/vl.f
cd $O
if [ "$MODE" = lint ]; then
  /usr/bin/time -v $VL --lint-only --timing -f vl.f > lint.log 2>&1; rc=$?
  echo "LINT rc=$rc errors $(grep -c '^%Error' lint.log) $(grep 'Maximum resident' lint.log)"; exit $rc
fi
J=${J:-48}
/usr/bin/time -v $VL --binary --timing -O1 --x-assign fast --x-initial fast --output-split 20000 --output-groups 256 \
  -j $J --build-jobs $J -CFLAGS -O1 -Mdir obj -f vl.f > build.log 2>&1; rc=$?
echo "BUILD rc=$rc errors $(grep -c '^%Error' build.log) $(grep -E 'Maximum resident|Elapsed' build.log | tr -s ' ' | tr '\n' ' ')"
exit $rc
