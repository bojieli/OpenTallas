#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-wbq-group4-map-1106
for lane in 0 4; do
 sudo docker run --rm --name "wbq-group4-map-${lane}-$PPID" --memory=4g --memory-swap=4g --cpus=2 -u "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock bash "/work/base${lane}/area.sh"
done
