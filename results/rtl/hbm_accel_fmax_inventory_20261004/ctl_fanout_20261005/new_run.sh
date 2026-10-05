#!/usr/bin/env bash
set -uo pipefail
job=/srv/opentallas-scratch/jobs/sagan-ctl-spec-drain-seeds9-16-r1
pids=()
for seed in {9..16}; do
 /srv/opentallas-scratch/admit.sh 2 -- bash "$job/seed.sh" "$seed" > "$job/admission$seed.log" 2>&1 &
 pids+=("$!")
 printf '%s %s\n' "$seed" "$!" >> "$job/children.pids"
done
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
printf '%s\n' "$rc" > "$job/exit"
exit "$rc"
