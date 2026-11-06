#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-hbm-wbqroot-store
docker run --rm --memory 12g --cpus 8 -u "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock bash /work/ctl_area.sh
