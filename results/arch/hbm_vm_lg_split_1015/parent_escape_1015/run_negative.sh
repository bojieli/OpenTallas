#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/lg-parent-escape-input
set +e
docker run --rm -e MODE=blocked -v "$PWD:/work" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 2 -exit /work/run.tcl' > blocked.log 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > blocked.exit
if [ "$rc" -eq 0 ]; then echo 'LG_PARENT BLOCKED MUTANT ESCAPED'; exit 1; fi
if ! grep -E 'DRT-0073|No access point' blocked.log; then echo 'LG_PARENT unexpected failure; not proof'; tail -12 blocked.log; exit 2; fi
echo 'LG_PARENT BLOCKED MUTANT REJECTED by actual pin-access error'
