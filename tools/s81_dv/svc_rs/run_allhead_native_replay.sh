#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?outdir}")
ROWS=${ROWS:-32}
FEEDBACK=${ALLHEAD_FEEDBACK:?actual allhead feedback capsule required}
CACHE=${NATIVE_REPLAY_CACHE:-/srv/opentallas-scratch2/claude/hard-s81-svc-1/native_programme/out/obj}
PRIVATE=${NATIVE_PRIVATE_ARCHIVE:-/srv/opentallas-scratch2/claude/hard-s81-svc-1/returned_p_replay/out_live/model_private.a}
V=${VERILATOR_INCLUDE:-$HOME/.local/opentallas-tools/verilator-5.050/share/verilator/include}
mkdir -p "$O"
sha256sum "$CACHE/Vtb_svc_native_programme__ALL.a" "$PRIVATE" >"$O/archive_before.sha256"
g++ -O0 -std=c++20 -I"$CACHE" -I"$V" -I"$V/vltstd" tools/s81_dv/svc_rs/svc_allhead_native_replay.cpp "$PRIVATE" "$CACHE/verilated.o" "$CACHE/verilated_timing.o" "$CACHE/verilated_threads.o" -pthread -latomic -o "$O/replay" >"$O/build.log" 2>&1
"$O/replay" "$ROWS" "$FEEDBACK/returned_hb0.hex" "$FEEDBACK/returned_hb1.hex" "$FEEDBACK/score_hb0.hex" "$FEEDBACK/score_hb1.hex" "$FEEDBACK/dates.hex" >"$O/run.log" 2>&1
grep -E '^ALLHEAD_(NATIVE_|RETENTION)' "$O/run.log"
grep -q '^ALLHEAD_NATIVE_REPLAY PASS' "$O/run.log"
sha256sum -c "$O/archive_before.sha256" >"$O/archive_after.log"
