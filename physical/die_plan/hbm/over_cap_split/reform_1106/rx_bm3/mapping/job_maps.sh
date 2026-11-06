#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-rx-bm3-native-1106
sudo docker run --rm --name "rx-bm3-map-$PPID" --memory=4g --memory-swap=4g --cpus=2 -u "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock bash /work/run_maps.sh
