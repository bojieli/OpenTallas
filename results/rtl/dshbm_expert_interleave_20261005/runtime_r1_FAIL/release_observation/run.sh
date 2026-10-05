#!/bin/bash
set -euo pipefail
export TMPDIR=/srv/opentallas/jobs-overflow/hubble-wg-release-observe-r1/tmp
mkdir -p "$TMPDIR"
O=/srv/opentallas/jobs-overflow/hubble-wg-release-observe-r1
B=/srv/opentallas/jobs-overflow/hubble-expert-interleave-r1
A=$B/native/connected/obj
cd "$O"
date -u > start.txt
awk "/MemAvailable/{print}" /proc/meminfo > headroom.txt
df -B1 "$O" >>headroom.txt
sha256sum "$A"/*.a "$A"/verilated*.o "$A"/Vtb_hbm_accel_expert_fetch_wg___024root.h "$B"/retained_wg_release_timeout.cpp "$B"/native/L20_stack0/{gu.hex,sm_expected.hex,gold.hex,x.hex} > inputs.sha256
g++ -Os -std=c++20 -fcoroutines -pthread -I"$A" -I/usr/share/verilator/include -I/usr/share/verilator/include/vltstd -c "$B"/retained_wg_release_timeout.cpp -o terminal.o > compile.log 2>&1
g++ -pthread terminal.o "$A"/Vtb_hbm_accel_expert_fetch_wg__ALL.a "$A"/verilated.o "$A"/verilated_threads.o "$A"/verilated_timing.o -latomic -o observe >>compile.log 2>&1
sha256sum observe > binary.sha256
./observe +DIR="$B/native/L20_stack0" +sm_slot=0 +notice_lead_ps=300000 +id0=41 +id1=65 +id2=158 +id3=164 +id4=259 +id5=266 > terminal.log 2>&1
sha256sum -c inputs.sha256 > postcheck.txt
date -u > terminal.txt
