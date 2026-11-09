#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-s81-rck-0222/work
R=$PWD;E=$R/results/s81_rck_11_reform_1108/column_faces
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
export TMPDIR=/srv/opentallas-scratch2/claude/codex-s81-rck-0222/tmp
for m in base RCKRF_MUT_XFACE_DELAY RCKRF_MUT_LKFACE_SHORT; do
 ARGS=();if [ "$m" != base ];then ARGS+=("$m");fi
 set +e
 bash "$E/run.sh" /srv/opentallas-scratch2/claude/codex-s81-rck-0222/column_inputs "$R/rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv" "$R/rtl/dsrom_sys/s81_link/col/ot_s81_rck_reform.sv" "$E/stubs.sv" "${ARGS[@]}" > "$E/$m.log" 2>&1
 rc=$?
 set -e
 tail -n 8 "$E/$m.log"
 if [ "$m" = base ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'RF lockstep FAILED' "$E/$m.log";fi
 printf '%s rc=%s expected=%s\n' "$m" "$rc" "$([ "$m" = base ] && echo PASS || echo MUTANT_CAUGHT)" >> "$E/summary.log"
done
