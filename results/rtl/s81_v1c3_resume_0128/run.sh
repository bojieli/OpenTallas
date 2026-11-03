#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ds-v1c3-serial-0128
O=/home/ubuntu/scratch-root/claude/tok-ds-2/build_v1c3
cd "$R"
printf 'RESUME_INCREMENTAL_SERIAL_START %s\n' "$(date -Is)" >> status
# Pinned existing hierarchy/source/cache; no frontend regeneration command, no source edits.
export OT_VL_JCAP=0
/usr/bin/time -v -o resume_make.time make -C "$O/obj" -f Vtb_s81_die_hier.mk hier_build -j1 > resume_make.log 2> resume_make.err
printf 'HIERARCHY_DONE %s\n' "$(date -Is)" >> status
/usr/bin/time -v -o top_make.time make -C "$O/obj" -f Vtb_s81_die.mk -j1 > top_make.log 2> top_make.err
printf 'BUILD_DONE %s\n' "$(date -Is)" >> status
# Retain original runner bytes and build failure; invoke the unchanged existing native run sequence.
B="$O/obj/Vtb_s81_die" O="$R/run" W=/srv/opentallas-scratch2/claude/tok-ds-2/chk bash "$R/run_v1c_serial.sh" > run.log 2> run.err
printf 'RUN_DONE %s\n' "$(date -Is)" >> status
