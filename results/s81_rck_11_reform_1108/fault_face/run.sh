#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-s81-rck-0222/work
R=$PWD; E=$R/results/s81_rck_11_reform_1108/fault_face
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
mkdir -p /srv/opentallas-scratch2/claude/codex-s81-rck-0222/tmp
if [ $# -eq 0 ];then set -- base RCKRF_MUT_FAULT_DELAY RCKRF_MUT_FAULT_NORST;fi
for m in "$@"; do
 D=$(mktemp -d /srv/opentallas-scratch2/claude/codex-s81-rck-0222/tmp/fault.XXXXXX)
 ARGS=();if [ "$m" != base ];then ARGS+=("-D$m");fi
 verilator --binary --timing -j 4 -O1 -Wno-fatal --top-module tb --Mdir "$D/obj" -o tb -I"$R/rtl/dsrom_sys/s81_link" "${ARGS[@]}" "$E/tb_fault.sv" "$R/rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv" "$R/rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv" > "$E/build_$m.log" 2>&1
 set +e
 "$D/obj/tb" > "$E/$m.log" 2>&1
 rc=$?
 set -e
 cat "$E/$m.log"
 if [ "$m" = base ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'fault face lockstep FAIL' "$E/$m.log";fi
 printf '%s rc=%s expected=%s\n' "$m" "$rc" "$([ "$m" = base ] && echo PASS || echo MUTANT_CAUGHT)" >> "$E/summary.log"
done
