#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-hbm-wbqroot-store/family_common
for mode in good mutant;do
 def=-DOT_WBQ_ROOT_STORE_FACES;[ "$mode" = good ] || def="-DOT_WBQ_ROOT_STORE_FACES -DROOT_STORE_MUT"
 mkdir -p "$mode"
 docker run --rm --memory 4g --cpus 2 -u "$(id -u):$(id -g)" -v "$PWD:/work" -v "$HOME/.local/opentallas-tools:$HOME/.local/opentallas-tools:ro" -e OBJCACHE= -e HOME="$HOME" -w /work python:3.12 bash -c '$HOME/.local/opentallas-tools/bin/verilator --binary -j 2 -Wno-fatal --top-module tb -Mdir "$1/obj" -o sim $2 tb.sv ref.sv new.sv ot_hbm_accel_cdc_fifo.sv ot_reset_sync.sv ot_hbm_face_reg.sv sram.sv > "$1/build.log" 2>&1; "$1/obj/sim" > "$1/sim.log" 2>&1' bash "$mode" "$def" || true
 tail -3 "$mode/sim.log"
done

grep -q "^PASS" good/sim.log
grep -q "FAIL" mutant/sim.log
