#!/bin/bash
set -u
cd /srv/opentallas/repos/rawls-die-em-result || exit 1
job=/srv/opentallas-scratch/codex/die-em-item8-20261005/qwen-spine_hub-r1
date -u +%FT%TZ > "$job/start.txt"
/srv/opentallas-scratch/admit.sh 32 -- /usr/bin/time -v -o "$job/resources.txt" python3 tools/die_window_em.py run --work "$job" --threads 8 > "$job/launcher.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$job/launcher.exit"
date -u +%FT%TZ > "$job/end.txt"
exit "$rc"
