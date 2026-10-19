#!/usr/bin/env bash
# VEH-FMT-COLL2/HC pre-check: build tb_hc_replay (Verilator 5.050) on the sw2-bundle masters, run every *.events.txt
set -u
H=$(cd "$(dirname "$0")" && pwd)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
LIB=($H/ot_hbm_host_cfg_leaf_sw.sv $H/hfd_hgi_vm_calendar_f20.sv $H/ot_hbm_hc_qhub_static.sv $H/ot_hgi_sfu_lg_pair_tap_leaf_term.sv)
sha256sum "${LIB[@]}" $H/tb_hc_replay.sv > $H/sources.sha256
$V --version > $H/verilator.version
if [ ! -x $H/obj/Vtb_hc_replay ]; then
  "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
    --top-module tb_hc_replay --Mdir $H/obj $H/tb_hc_replay.sv "${LIB[@]}" > $H/build.log 2>&1 || { tail -30 $H/build.log; exit 2; }
fi
rc=0
for f in $H/${GLOB:-*}.events.txt; do
  n=$(basename $f .events.txt)
  $H/obj/Vtb_hc_replay +EV=$f ${PLUS:-} > $H/$n.log 2>&1
  r=$(grep -m1 -E '^HCRPL (PASS|FAIL)' $H/$n.log); echo "$n: $r"; grep -m3 -E 'MISMATCH|internal fault|TRACE' $H/$n.log
  case $n in mut_*) echo "$r" | grep -q FAIL || rc=1;; *) echo "$r" | grep -q PASS || rc=1;; esac
done
exit $rc
