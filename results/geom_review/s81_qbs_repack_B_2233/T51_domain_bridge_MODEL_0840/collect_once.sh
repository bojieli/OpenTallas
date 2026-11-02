#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-t51-domain-bridge-0840
cd "$R"
(set -C; : > collection.once)
docker run --rm --memory=4g --memory-swap=4g --cpus=1 -e HUID="$(id -u)" -e HGID="$(id -g)" -v "$R:/work" openroad/orfs:asap7lock bash -c 'trap '\''chown -R "$HUID:$HGID" /work'\'' EXIT; python3 /work/collect_existing.py > /work/collection.log 2>&1'
