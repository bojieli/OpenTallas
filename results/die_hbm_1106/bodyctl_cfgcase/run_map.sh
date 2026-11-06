#!/bin/bash
set -euo pipefail
docker run --rm --cpus=2 --memory=8g -v /srv/opentallas-scratch2/claude/codex-bodyctl-cfgcase:/work openroad/orfs:asap7lock bash /work/map.sh
