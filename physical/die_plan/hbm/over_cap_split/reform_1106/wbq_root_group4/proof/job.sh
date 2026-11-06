#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-wbq-group4-proof-1106
for mode in raw_default raw_group family_default family_group mut_groupwire mut_lane mut_dropwd; do
 def=; extra=
 case "$mode" in raw*) ;; *) def=-DOT_WBQ_ROOT_STORE_FACES; extra=ot_hbm_face_reg.sv;; esac
 rc=0
 sudo docker run --rm --name "wbq-group4-${mode}-$PPID" --memory=4g --memory-swap=4g --cpus=2 -u "$(id -u):$(id -g)" -v "$PWD:/proof" -v "$HOME/.local/opentallas-tools:$HOME/.local/opentallas-tools:ro" -e HOME="$HOME" -e OBJCACHE= -w "/proof/$mode" python:3.12 bash -c '$HOME/.local/opentallas-tools/bin/verilator --binary -j 2 -Wno-fatal --top-module tb -Mdir obj -o sim $1 tb.sv ref.sv new.sv ot_hbm_accel_cdc_fifo.sv ot_reset_sync.sv sram.sv $2 > build.log 2>&1 && ./obj/sim > sim.log 2>&1' bash "$def" "$extra" || rc=$?
 printf '%s\n' "$rc" > "$mode/exit.rc"
 tail -n 4 "$mode/sim.log"
 case "$mode" in mut*) grep -q 'FAIL' "$mode/sim.log";; *) test "$rc" = 0;grep -q '^PASS' "$mode/sim.log";; esac
done
printf 'ALL_VEHICLES_PASS\n' > result.txt
