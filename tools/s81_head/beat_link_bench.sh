#!/usr/bin/env bash
# S81-HEAD/ADAPT beat-link bench (Verilator 5.050, the daemon's pinned version).  usage: beat_link_bench.sh OUTDIR
# (repo root cwd).  Cases: 553 -> 2 beats (lane record over the 276-class host lane), 1104 -> 4 beats (HBC ring word),
# 64 -> 1 beat (mesh), 276 -> 1 beat (H4 tl/ca/cb); seeds 1..3; mutants 1 (beat swap), 2 (dropped beat), 3 (TX rate
# check removed + rate violation) on the two multi-beat cases.  A good run prints PASS, a mutant run must print FAIL.
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; D=rtl/dsrom_sys/s81_head
mkdir -p "$O"; rc=0
run() {  # name W N S MUT expect [IDLE_ZERO HOLD_REAL PFIX]
  local n=$1 W=$2 N=$3 S=$4 M=$5 E=$6 IZ=${7:-0} HR=${8:-0} PF=${9:-0}; mkdir -p "$O/$n"
  "$VL" --binary --top-module tb_s81hd_beat_link -Mdir "$O/$n/obj" -j 4 -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDPARAM \
    -GW=$W -GN=$N -GS=$S -GMUT=$M -GNREC=1200 -GIDLE_ZERO=$IZ -GHOLD_REAL=$HR -GPFIX=$PF \
    $D/ot_s81hd_beat_link.sv $D/test/tb_s81hd_beat_link.sv > "$O/$n/build.log" 2>&1 \
    || { echo "$n BUILD FAIL"; tail -5 "$O/$n/build.log"; rc=1; return; }
  for s in 1 2 3; do
    "$O/$n/obj/Vtb_s81hd_beat_link" +seed=$s > "$O/$n/run_s$s.log" 2>&1
    r=$(grep -E '^BEAT_LINK' "$O/$n/run_s$s.log" | awk '{print $NF}')
    v=$([ "$r" = "$E" ] && echo OK || echo BAD); [ $v = OK ] || rc=1
    echo "$n s$s expect=$E got=${r:-NONE} $v | $(grep -E '^BEAT_LINK' "$O/$n/run_s$s.log")"
  done
}
for c in "r553 553 2 2" "h1104 1104 4 2" "m64 64 1 1" "t276 276 1 1"; do set -- $c; run $1 $2 $3 $4 0 PASS; done
for c in "r553 553 2 2" "h1104 1104 4 2"; do set -- $c; for m in 1 2 3; do run ${1}_mut$m $2 $3 $4 $m FAIL; done; done
# DIE-HEAD-71 (hd_ctl LEC): the two hd_ctl TX points (best64 W97 N2 P62, host276 W553 N3 P273, IDLE_ZERO 1) with the pad-free
# hold (HOLD_REAL 1) and without it; mutants 2 / 3 on the HOLD_REAL points must still be caught
for c in "b97 97 2 2 62" "h553 553 3 2 273"; do set -- $c
  run ${1}_hr0 $2 $3 $4 0 PASS 1 0 $5; run ${1}_hr1 $2 $3 $4 0 PASS 1 1 $5
  for m in 2 3; do run ${1}_hr1_mut$m $2 $3 $4 $m FAIL 1 1 $5; done
done
grep -h "Warning-" "$O"/r553/build.log "$O"/h1104/build.log | sort | uniq -c | head -20
echo "BEAT_LINK_BENCH rc=$rc"; exit $rc
