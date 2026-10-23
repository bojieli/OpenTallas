#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/codex-s81-rtlgap-2140-1022
cd "$R/K_producer2"
mkdir -p "$R/out_producer"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > "$R/out_producer/verilator.version"
sha256sum $(grep -v '^+' kit.f) > "$R/out_producer/sources.sha256"
/usr/bin/time -v -o "$R/out_producer/build.time" "$V" --binary --timing -j 2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT --top-module tb_dsdv_seq_host_mu -f kit.f "$R/tb_dsdv_seq_host_mu.sv" --Mdir "$R/out_producer/obj" -o sim > "$R/out_producer/build.log" 2>&1
N=$(wc -l < "$R/job15/prog/host_boot.memh")
"$R/out_producer/obj/sim" +dir="$R/job15" +n="$N" +cyc=1000 +timeout=4000 +mu="$R/job15/mu.txt" > "$R/out_producer/run.log" 2>&1
python3 "$R/check_producer.py" "$R/job15" "$R/out_producer/run.log" "$R/out_producer/check.json"
