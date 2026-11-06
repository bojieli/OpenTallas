#!/bin/bash
set -u
K=/srv/opentallas-scratch2/claude/s81-wave-1105f2/kit-wave/s81/bf1e2233ce05/items/dsdv_slice_lepe_mu_C__t1/attempt_3/gen/dsdv_slice_lepe_mu_C__t1
O=/srv/opentallas-scratch2/claude/codex-lec-unroll-1106
IMAGE=openroad/orfs:asap7lock
sudo docker image inspect "$IMAGE" --format '{{.Id}}' > "$O/image_id.txt"
sudo docker run --rm --memory=16g --memory-swap=16g -v "$K:/work:ro" -v "$O:/proof" "$IMAGE" bash -c '/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -T -p "help read_slang"' > "$O/read_slang_help.log" 2>&1
sudo docker run --rm --memory=16g --memory-swap=16g -v "$K:/work:ro" -v "$O:/proof" "$IMAGE" bash -c '/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -T -l /proof/lint_limit.log -s /proof/lint_limit.ys' > "$O/lint_limit.stdout" 2>&1
RC=$?
printf '%s\n' "$RC" > "$O/lint_limit.rc"
if test "$RC" -ne 0; then tail -n 20 "$O/lint_limit.log"; exit "$RC"; fi
sudo docker run --rm --memory=16g --memory-swap=16g -v "$O:/proof" "$IMAGE" bash -c '/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -T -l /proof/negative.log -s /proof/negative.ys' > "$O/negative.stdout" 2>&1
NRC=$?
printf '%s\n' "$NRC" > "$O/negative.rc"
if test "$NRC" -eq 0 || ! grep -q 'unroll limit of 32912 exhausted' "$O/negative.log"; then tail -n 20 "$O/negative.log"; exit 3; fi
printf 'ACTUAL_FRONTEND_PASS_FINITE_LIMIT_NEGATIVE_CAUGHT\n'
