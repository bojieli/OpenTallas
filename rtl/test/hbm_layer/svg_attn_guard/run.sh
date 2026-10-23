#!/usr/bin/env bash
# STEWARD-HBMd 10-22: SVG S1 consumer-copy guard (MVPKT) bench on the authentic PV calendar + native KV packets.
# Inputs: old.mem (PV cal.cyc SVG command words, bit25 kept = main emitter), packet.mem (cal.pkt), from codex feed_min
# (input_receipt_codex.json).  Run through ot-run: ot-run --mem 4 --threads 2 --dir <copy of this dir> -- bash run.sh
set -eu; cd "$(dirname "$0")"; R=$(git rev-parse --show-toplevel 2>/dev/null || echo ../../../..)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing --top-module tb -j 2 -Wno-fatal --Mdir obj "$R/rtl/hbm_accel/sm/static/ot_smh_static_feed.sv" tb_svg_attn_guard.sv > build.log 2>&1
obj/Vtb | tee run.log | grep -E 'SVG_ATTN_GUARD_(PASS|FAIL)'
