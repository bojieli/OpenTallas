#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-hist-clock-model-r3-complete-0442
cd "$R"
(set -C; : > model.once)
docker run --rm --memory=4g --memory-swap=4g --cpus=1 -e HUID="$(id -u)" -e HGID="$(id -g)" -v "$R:/work" openroad/orfs:asap7lock bash -c 'trap '\''chown -R "$HUID:$HGID" /work'\'' EXIT; python3 /work/model.py > /work/model.log 2>&1'
